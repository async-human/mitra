"""Founder onboarding chat endpoint — REST API for the web onboarding UI."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from mitra_api.agent.session_store import AgentSessionStore, build_session_store
from mitra_api.config import Settings, get_settings
from mitra_api.founder.jd_parser import extract_jd_signals, extract_jd_text
from mitra_api.founder.prompts import FOUNDER_SYSTEM_PROMPT
from mitra_api.llm.factory import get_llm_adapter
from mitra_api.llm.types import ChatMessage, ToolDefinition

log = logging.getLogger(__name__)

router = APIRouter(prefix="/founder", tags=["founder"])

_SESSION_PREFIX = "founder"

_RESPOND_TOOL = ToolDefinition(
    name="respond",
    description=(
        "You MUST call this tool for every response — no exceptions. "
        "Pass your conversational reply to the founder, any hiring signals "
        "extracted from their message, and optional quick-reply chips."
    ),
    parameters={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": (
                    "Your conversational reply (2-4 sentences max, one question only). "
                    "Use *bold* for emphasis."
                ),
            },
            "signals": {
                "type": "object",
                "description": (
                    "Key-value map of NEW hiring signals from the founder's latest message. "
                    "Use {} if the founder didn't share any new facts this turn. "
                    "Valid keys: role_title, first_90_days, dealbreaker, culture_signal, "
                    "salary_range, location, company_name, why_join, stage, intro_preference, contact_info."
                ),
            },
            "quick_replies": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "2-4 short reply options shown as chips in the UI. "
                    "Use [] for open-ended questions where free text is better."
                ),
            },
        },
        "required": ["message", "signals", "quick_replies"],
    },
)

_founder_store: AgentSessionStore | None = None


def _get_store(settings: Settings) -> AgentSessionStore:
    global _founder_store
    if _founder_store is None:
        _founder_store = build_session_store(settings)
    return _founder_store


def _session_key(session_id: str) -> str:
    return f"{_SESSION_PREFIX}:{session_id}"


_STEPS = ("role", "brief", "details", "context", "contact")


def _compute_step_progress(signals: dict[str, Any]) -> tuple[str, int, bool]:
    """Return (current_active_step, progress_pct, is_complete)."""
    has = lambda *keys: any(k in signals for k in keys)

    role_done    = has("role_title")
    brief_done   = role_done and has("first_90_days") and has("dealbreaker", "culture_signal")
    details_done = brief_done and has("salary_range")
    context_done = details_done and has("company_name") and has("why_join", "stage")
    pref_done    = context_done and has("intro_preference")
    contact_done = pref_done and has("contact_info")

    if contact_done:  return "contact", 100, True
    if pref_done:     return "contact",  94, False
    if context_done:  return "contact",  88, False
    if details_done:  return "context",  72, False
    if brief_done:    return "details",  55, False
    if role_done:     return "brief",    22, False
    return "role", 5, False


# ── Signal → Job mapping helpers ─────────────────────────────────────────────

def _parse_salary(raw: str) -> tuple[int | None, int | None]:
    """'20-35 LPA' | '₹25 lakh' | '30' → (lo, hi) integers in LPA."""
    nums = [int(n) for n in re.findall(r'\d+', raw)]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def _infer_remote_policy(location: str | None) -> str | None:
    if not location:
        return None
    loc = location.lower()
    if "remote" in loc:
        return "remote"
    if "hybrid" in loc:
        return "hybrid"
    return "onsite"


def _route_contact(intro_pref: str, contact: str) -> tuple[str | None, str | None]:
    """Return (founder_wa, founder_email) based on intro preference."""
    pref = intro_pref.lower()
    if "whatsapp" in pref or "wa" in pref or "phone" in pref or "number" in pref:
        return contact, None
    if "email" in pref or "mail" in pref:
        return None, contact
    # Infer from contact format
    if "@" in contact:
        return None, contact
    return contact, None


async def _auto_submit_job(session_id: str, signals: dict[str, Any]) -> None:
    """
    Background task: persist a completed founder brief as a Job row.
    Uses external_id='founder:<session_id>' for idempotency — safe to call
    multiple times for the same session.
    """
    # Lazy imports — only needed when DB is configured
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job, JobStatus
    from mitra_api.jobs.admin import _generate_and_store_embedding

    title   = (signals.get("role_title")   or "").strip()
    company = (signals.get("company_name") or "").strip()

    if not title:
        log.warning("founder submit: missing role_title for session %s — skipping", session_id)
        return

    if not company:
        company = "Unknown Company"
        log.warning("founder submit: company_name missing for session %s — using fallback", session_id)

    external_id = f"founder:{session_id}"
    factory = get_session_factory()

    async with factory() as db:
        # Idempotency: skip if already submitted
        existing = (await db.execute(
            select(Job).where(Job.external_id == external_id)
        )).scalar_one_or_none()

        if existing:
            log.info("founder submit: job already exists (id=%d) for session %s", existing.id, session_id)
            return

        sal_min, sal_max = _parse_salary(signals.get("salary_range") or "")
        location         = signals.get("location")
        remote_policy    = _infer_remote_policy(location)

        summary_parts = []
        if signals.get("why_join"):
            summary_parts.append(signals["why_join"])
        if signals.get("first_90_days"):
            summary_parts.append(f"First 90 days: {signals['first_90_days']}")

        # Core signal keys that map to dedicated Job columns — everything else is extra
        _CORE_KEYS = {
            "role_title", "company_name", "stage", "location", "salary_range",
            "first_90_days", "dealbreaker", "culture_signal", "why_join",
            "intro_preference", "contact_info",
        }
        extra_signals = {k: v for k, v in signals.items() if k not in _CORE_KEYS and v}

        # job.signals JSONB stores culture/dealbreaker context + all extra signals
        job_signals: dict = {}
        if signals.get("culture_signal"):
            job_signals["culture_signal"] = signals["culture_signal"]
        if signals.get("dealbreaker"):
            job_signals["dealbreaker"] = signals["dealbreaker"]
        job_signals.update(extra_signals)

        contact      = (signals.get("contact_info") or "").strip()
        intro_pref   = signals.get("intro_preference") or ""
        founder_wa, founder_email = _route_contact(intro_pref, contact) if contact else (None, None)

        job = Job(
            external_id=external_id,
            status=JobStatus.active,
            title=title,
            company=company,
            stage=signals.get("stage"),
            location=location,
            remote_policy=remote_policy,
            employment="full_time",
            salary_min_lpa=sal_min,
            salary_max_lpa=sal_max,
            signals=job_signals or None,
            summary=" | ".join(summary_parts) or None,
            founder_wa=founder_wa,
            founder_email=founder_email,
        )
        db.add(job)
        await db.flush()

        await _generate_and_store_embedding(job, db)
        await db.commit()

        log.info(
            "founder submit: job created id=%d external_id=%s (%s @ %s)",
            job.id, external_id, title, company,
        )


# ── Request / Response schemas ────────────────────────────────────────────────

class FounderChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=200)
    message: str    = Field(default="", max_length=4000)


class FounderChatResponse(BaseModel):
    reply: str
    signals: dict[str, Any]
    step: str
    progress: int
    complete: bool
    quick_replies: list[str]


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@router.post("/chat", response_model=FounderChatResponse)
async def founder_chat(
    body: FounderChatRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> FounderChatResponse:
    store   = _get_store(settings)
    adapter = get_llm_adapter(settings)
    sid     = _session_key(body.session_id)
    is_init = not body.message.strip()

    # Load prior context
    transcript       = await store.get_transcript(sid)
    existing_signals = await store.get_signals(sid)

    # Build message list
    msgs: list[ChatMessage] = [ChatMessage(role="system", content=FOUNDER_SYSTEM_PROMPT)]
    msgs.extend(transcript)

    if existing_signals:
        msgs.append(ChatMessage(
            role="system",
            content="Signals collected so far: " + json.dumps(existing_signals, ensure_ascii=False),
        ))

    user_content = (
        body.message.strip() if not is_init
        else "[CONVERSATION START — call respond() with your opening greeting now]"
    )
    msgs.append(ChatMessage(role="user", content=user_content))
    persist_from = len(msgs) - 1

    result = await adapter.complete(
        model=settings.mitra_llm_model,
        messages=msgs,
        tools=[_RESPOND_TOOL],
        max_tokens=settings.mitra_llm_max_tokens,
        temperature=settings.mitra_llm_temperature,
        force_tool="respond",
    )

    respond_call = next(
        (tc for tc in (result.tool_calls or []) if tc.name == "respond"),
        None,
    )

    new_signals: dict[str, Any] = {}
    quick_replies: list[str]    = []

    if respond_call:
        try:
            args = json.loads(respond_call.arguments or "{}")
        except json.JSONDecodeError:
            args = {}

        final_text    = str(args.get("message") or "").strip()
        raw_signals   = args.get("signals") or {}
        new_signals   = {str(k): str(v) for k, v in raw_signals.items() if v is not None and str(v).strip()}
        quick_replies = [str(r) for r in (args.get("quick_replies") or [])[:4] if r]

        if new_signals:
            await store.merge_signals(sid, new_signals)

        if not final_text:
            final_text = "Could you tell me a bit more?"

    else:
        final_text = (result.content or "").strip() or "Could you tell me a bit more?"
        log.warning("founder_chat: respond tool not called for session %s — text fallback", sid)

    # Persist transcript
    assistant_msg = ChatMessage(role="assistant", content=final_text)
    msgs.append(assistant_msg)

    if is_init:
        anchor = ChatMessage(role="user", content="[start]")
        await store.append_messages(sid, [anchor, assistant_msg])
    else:
        await store.append_messages(sid, msgs[persist_from:])

    # Compute UI state
    all_signals = await store.get_signals(sid)
    step, progress, complete = _compute_step_progress(all_signals)

    # Auto-submit to DB when onboarding completes (only if DB is configured)
    if complete and settings.mitra_database_url:
        background_tasks.add_task(_auto_submit_job, body.session_id, all_signals)

    return FounderChatResponse(
        reply=final_text,
        signals=all_signals,
        step=step,
        progress=progress,
        complete=complete,
        quick_replies=quick_replies,
    )


# ── JD upload endpoint ────────────────────────────────────────────────────────

_ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/octet-stream",  # some browsers send this for .docx
}
_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/upload-jd", response_model=FounderChatResponse)
async def founder_upload_jd(
    background_tasks: BackgroundTasks,
    session_id: str      = Form(...),
    file: UploadFile     = File(...),
    settings: Settings   = Depends(get_settings),
) -> FounderChatResponse:
    """
    Accept a PDF or DOCX job description, extract hiring signals, merge them
    into the session, then return the agent's natural follow-up asking only
    about what's still missing — same response shape as /founder/chat.
    """
    # ── Validate file ─────────────────────────────────────────────────────────
    filename = file.filename or ""
    if not (filename.lower().endswith(".pdf")
            or filename.lower().endswith(".docx")
            or filename.lower().endswith(".doc")):
        raise HTTPException(400, "Only PDF and Word (.docx / .doc) files are supported.")

    raw = await file.read()
    if len(raw) > _MAX_FILE_BYTES:
        raise HTTPException(413, "File too large — maximum 10 MB.")
    if not raw:
        raise HTTPException(400, "Uploaded file is empty.")

    # ── Extract text then signals ─────────────────────────────────────────────
    text = await extract_jd_text(raw, filename)
    if not text or len(text) < 30:
        raise HTTPException(422, "Could not extract readable text from the file.")

    extracted = await extract_jd_signals(text, settings)

    # ── Merge into session store ──────────────────────────────────────────────
    store = _get_store(settings)
    sid   = _session_key(session_id)

    if extracted:
        await store.merge_signals(sid, extracted)

    # ── Build agent turn — acknowledge + ask for what's missing ──────────────
    transcript    = await store.get_transcript(sid)
    all_signals   = await store.get_signals(sid)
    adapter       = get_llm_adapter(settings)

    extracted_summary = json.dumps(extracted, ensure_ascii=False, indent=None)
    user_content = (
        f"[Founder uploaded a JD file: '{filename}'. "
        f"Automatically extracted signals: {extracted_summary}. "
        "Acknowledge what was successfully parsed (mention the role and company), "
        "then ask for the single most important piece of information still missing.]"
    )

    msgs: list[ChatMessage] = [ChatMessage(role="system", content=FOUNDER_SYSTEM_PROMPT)]
    msgs.extend(transcript)

    if all_signals:
        msgs.append(ChatMessage(
            role="system",
            content="Signals collected so far: " + json.dumps(all_signals, ensure_ascii=False),
        ))

    msgs.append(ChatMessage(role="user", content=user_content))

    result = await adapter.complete(
        model=settings.mitra_llm_model,
        messages=msgs,
        tools=[_RESPOND_TOOL],
        max_tokens=settings.mitra_llm_max_tokens,
        temperature=settings.mitra_llm_temperature,
        force_tool="respond",
    )

    respond_call = next(
        (tc for tc in (result.tool_calls or []) if tc.name == "respond"),
        None,
    )

    quick_replies: list[str] = []

    if respond_call:
        try:
            args = json.loads(respond_call.arguments or "{}")
        except json.JSONDecodeError:
            args = {}

        final_text    = str(args.get("message") or "").strip()
        raw_signals   = args.get("signals") or {}
        new_signals   = {str(k): str(v) for k, v in raw_signals.items() if v is not None and str(v).strip()}
        quick_replies = [str(r) for r in (args.get("quick_replies") or [])[:4] if r]

        if new_signals:
            await store.merge_signals(sid, new_signals)

        if not final_text:
            role = extracted.get("role_title", "the role")
            final_text = f"Got it — I've read the JD for {role}. Let me ask about a few missing details."
    else:
        role = extracted.get("role_title", "the role")
        final_text = f"I've read through the JD for {role}. Let me ask about a few details."

    # ── Persist to transcript ─────────────────────────────────────────────────
    # Store as a clean user/assistant pair so the conversation stays coherent
    anchor        = ChatMessage(role="user",      content=f"[Uploaded JD: {filename}]")
    assistant_msg = ChatMessage(role="assistant", content=final_text)

    if not transcript:
        await store.append_messages(sid, [anchor, assistant_msg])
    else:
        await store.append_messages(sid, [anchor, assistant_msg])

    # ── Compute UI state ──────────────────────────────────────────────────────
    all_signals = await store.get_signals(sid)
    step, progress, complete = _compute_step_progress(all_signals)

    if complete and settings.mitra_database_url:
        background_tasks.add_task(_auto_submit_job, session_id, all_signals)

    return FounderChatResponse(
        reply=final_text,
        signals=all_signals,
        step=step,
        progress=progress,
        complete=complete,
        quick_replies=quick_replies,
    )


# ── Founder one-click response ────────────────────────────────────────────────

_RESPOND_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mitra — {title}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #F9F8F5;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }}
    .card {{
      background: #fff;
      border-radius: 20px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      max-width: 480px;
      width: 100%;
      padding: 48px 40px;
      text-align: center;
    }}
    .logo {{
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.04em;
      color: #0D0D0C;
      margin-bottom: 32px;
    }}
    .logo span {{ color: #1A7A4A; }}
    .icon {{
      width: 64px;
      height: 64px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 20px;
      font-size: 28px;
    }}
    .icon--green {{ background: #D1FAE5; }}
    .icon--grey  {{ background: #F3F4F6; }}
    .icon--red   {{ background: #FEE2E2; }}
    h1 {{
      font-size: 22px;
      font-weight: 700;
      color: #0D0D0C;
      margin-bottom: 10px;
      letter-spacing: -0.02em;
    }}
    p {{
      font-size: 15px;
      color: #6B7280;
      line-height: 1.6;
      margin-bottom: 8px;
    }}
    .highlight {{
      font-weight: 600;
      color: #0D0D0C;
    }}
    .note {{
      margin-top: 24px;
      padding: 16px;
      background: #F9F8F5;
      border-radius: 12px;
      font-size: 13px;
      color: #9CA3AF;
    }}
    .footer {{
      margin-top: 32px;
      font-size: 12px;
      color: #D1D5DB;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">Mitra<span>.</span></div>
    <div class="icon {icon_class}">{icon}</div>
    <h1>{heading}</h1>
    <p>{body_line1}</p>
    <p>{body_line2}</p>
    <div class="note">{note}</div>
    <div class="footer">Mitra — AI talent agent for funded startups</div>
  </div>
</body>
</html>"""


async def _notify_candidate_of_response(
    *,
    candidate_email: str,
    candidate_name: str,
    founder_name: str,
    company: str,
    job_title: str,
    action: str,
) -> None:
    """Send the candidate an email when a founder responds to their intro."""
    from mitra_api.tools.email import send_email

    if action == "interested":
        subject = f"Good news — {company} wants to connect · Mitra"
        body = (
            f"Hi {candidate_name},\n\n"
            f"Great news — {founder_name or 'the founder'} at {company} responded to your intro "
            f"for the {job_title} role and they're interested in connecting!\n\n"
            f"We'll coordinate next steps and reach out to you shortly.\n\n"
            f"— Mitra"
        )
    else:
        subject = f"Update on your intro to {company} · Mitra"
        body = (
            f"Hi {candidate_name},\n\n"
            f"{company} has reviewed your intro for the {job_title} role. "
            f"They mentioned it's not the right fit at this moment — but your profile is strong "
            f"and we're continuing to look for the best opportunities for you.\n\n"
            f"— Mitra"
        )

    try:
        await send_email(to=candidate_email, subject=subject, text=body)
    except Exception:
        log.warning("candidate response notification failed for %s (non-critical)", candidate_email)


@router.get("/respond", response_class=HTMLResponse)
async def founder_respond(
    token: str = Query(..., description="One-click response token from intro email"),
    action: str = Query(..., description="'interested' or 'not_a_fit'"),
) -> HTMLResponse:
    """
    One-click founder response endpoint linked from intro emails.
    Updates intro status and notifies the candidate — no login required.
    """
    from datetime import datetime, timezone
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Intro, Job, Candidate, IntroStatus

    valid_actions = ("interested", "not_a_fit")
    if action not in valid_actions:
        return HTMLResponse(_RESPOND_HTML.format(
            title="Invalid link",
            icon_class="icon--red", icon="✕",
            heading="Invalid link",
            body_line1="This response link is not valid.",
            body_line2="Please reply directly to the intro email if you have a question.",
            note="If you believe this is an error, reply to this email.",
        ), status_code=400)

    factory = get_session_factory()
    async with factory() as db:
        intro = (await db.execute(
            select(Intro).where(Intro.response_token == token)
        )).scalar_one_or_none()

        if not intro:
            return HTMLResponse(_RESPOND_HTML.format(
                title="Link expired",
                icon_class="icon--grey", icon="⏱",
                heading="Link already used or expired",
                body_line1="This response link has already been actioned.",
                body_line2="No further action is needed — we have your response on file.",
                note="Questions? Reply directly to the original intro email.",
            ), status_code=200)

        # Load related job and candidate
        job = (await db.execute(select(Job).where(Job.id == intro.job_id))).scalar_one_or_none()
        candidate = (await db.execute(
            select(Candidate).where(Candidate.id == intro.candidate_id)
        )).scalar_one_or_none()

        # Update status and invalidate token (one-use only)
        new_status = IntroStatus.acknowledged if action == "interested" else IntroStatus.declined
        intro.status = new_status
        intro.updated_at = datetime.now(timezone.utc)
        intro.response_token = None
        await db.commit()

        log.info("founder respond: intro_id=%d action=%s new_status=%s", intro.id, action, new_status)

    # Derive candidate contact info
    cand_name  = (candidate.name or "there") if candidate else "there"
    cand_email = ""
    if candidate and candidate.phone.startswith("web:"):
        cand_email = candidate.phone.removeprefix("web:").strip()

    company   = job.company   if job else "the company"
    job_title = job.title     if job else "the role"

    # Fire-and-forget candidate notification
    if cand_email and "@" in cand_email:
        import asyncio
        asyncio.create_task(_notify_candidate_of_response(
            candidate_email=cand_email,
            candidate_name=cand_name,
            founder_name=(job.founder_name or "") if job else "",
            company=company,
            job_title=job_title,
            action=action,
        ))

    if action == "interested":
        return HTMLResponse(_RESPOND_HTML.format(
            title="Response recorded",
            icon_class="icon--green", icon="✓",
            heading="Great — we'll make it happen.",
            body_line1=f"You marked <span class='highlight'>{cand_name}</span> as interested for the <span class='highlight'>{job_title}</span> role.",
            body_line2="We'll coordinate a time with them and follow up with you shortly.",
            note=f"The candidate has been notified. Expect a follow-up from Mitra within 24 hours.",
        ))
    else:
        return HTMLResponse(_RESPOND_HTML.format(
            title="Response recorded",
            icon_class="icon--grey", icon="✓",
            heading="Response noted — thank you.",
            body_line1=f"You let us know <span class='highlight'>{cand_name}</span> isn't the right fit right now.",
            body_line2="We'll keep looking and only reach out when we have a genuinely better match.",
            note="The candidate has been notified respectfully. No further action needed.",
        ))
