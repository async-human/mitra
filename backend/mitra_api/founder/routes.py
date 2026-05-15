"""Founder onboarding chat endpoint — REST API for the web onboarding UI."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import secrets as _secrets

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
from mitra_api.tools.intros import normalize_why_note_for_founder

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


_EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')
_PHONE_RE = re.compile(r'[\+]?[\d][\d\s\-\(\)]{8,}[\d]')


def _auto_extract_contact(user_message: str) -> str | None:
    """
    Fallback: if the user typed their email/phone directly but the LLM forgot to
    save it as a signal, extract it here.
    """
    email = _EMAIL_RE.search(user_message)
    if email:
        return email.group()
    phone = _PHONE_RE.search(user_message)
    if phone:
        return phone.group().strip()
    return None


def _missing_context_nudge(signals: dict[str, Any]) -> str | None:
    """
    Return a follow-up question if the agent wrapped up early without collecting
    all required fields. Returns None when everything is present.

    Catches two failure modes:
      A) contact_info collected but company context skipped
      B) intro_preference collected but contact_info not saved
    """
    has = lambda *keys: any(k in signals for k in keys)

    # ── Mode B: intro channel known but actual address missing ────────────────
    if has("intro_preference") and not has("contact_info"):
        pref = signals.get("intro_preference", "").lower()
        if "whatsapp" in pref or "phone" in pref or "wa" in pref:
            return "Could you share your WhatsApp number so I can send introductions? (include country code)"
        return "Could you share your email address so I can send introductions?"

    # ── Mode A: contact collected but company context skipped ─────────────────
    if not has("contact_info"):
        return None
    if has("company_name") and has("why_join", "stage"):
        return None

    if not has("company_name"):
        return (
            "One more thing before we're fully set — what's the company name? "
            "I want to make sure candidates know who they're being introduced to."
        )
    if not has("why_join") and not has("stage"):
        return (
            "Just two quick things: what's your funding stage, and what would genuinely "
            "excite the right engineer about joining? I use this to pitch the role to candidates."
        )
    if not has("why_join"):
        return (
            "Almost done — what would genuinely excite the right engineer about joining? "
            "This is how I pitch the role to candidates."
        )
    if not has("stage"):
        return "What's your current funding stage? (e.g. Seed, Series A, Series B)"
    return None


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


async def _auto_submit_job(session_id: str, signals: dict[str, Any], auth_email: str | None = None) -> None:
    """
    Background task: persist a completed founder brief as a Job row.
    Uses external_id='founder:<session_id>' for idempotency — safe to call
    multiple times for the same session.
    auth_email: the founder's OAuth sign-in email, used as fallback founder_email
    so /founder/setup can always find the job by auth identity.
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

        # Always ensure founder_email is set so /founder/setup can find this job by
        # the OAuth email. Prefer the derived email from contact_info; fall back to the
        # auth_email passed from the signed-in session.
        if not founder_email and auth_email:
            founder_email = auth_email.strip().lower()
            log.info("founder submit: using auth_email=%r as founder_email for session %s", founder_email, session_id)

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
            founder_name=signals.get("contact_info", "").split()[0] if signals.get("contact_info") else None,
            founder_access_token=_secrets.token_urlsafe(32),
        )
        db.add(job)
        await db.flush()

        await _generate_and_store_embedding(job, db)
        await db.commit()

        log.info(
            "founder submit: job created id=%d external_id=%s (%s @ %s)",
            job.id, external_id, title, company,
        )

        # Alert matching candidates now that the job is live
        from mitra_api.tools.notifications import notify_matching_candidates_bg
        await notify_matching_candidates_bg(job.id)


# ── Request / Response schemas ────────────────────────────────────────────────

class FounderChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=200)
    message: str    = Field(default="", max_length=4000)
    auth_email: str | None = Field(default=None, description="Signed-in founder's OAuth email (optional)")


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

    # ── Fallback: auto-extract contact_info if the LLM forgot to save it ─────
    after_llm_signals = await store.get_signals(sid)
    if (
        not is_init
        and "intro_preference" in after_llm_signals
        and "contact_info" not in after_llm_signals
    ):
        extracted = _auto_extract_contact(user_content)
        if extracted:
            await store.merge_signals(sid, {"contact_info": extracted})
            log.info("founder_chat: auto-extracted contact_info=%r for session %s", extracted, sid)

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

    # Guard: if the LLM wrapped up early but fields are still missing, override reply
    nudge = _missing_context_nudge(all_signals)
    if nudge and not complete:
        final_text = nudge
        quick_replies = []
        # Persist the corrected assistant message
        await store.append_messages(sid, [ChatMessage(role="assistant", content=final_text)])

    # Auto-submit to DB when onboarding completes (only if DB is configured)
    if complete and settings.mitra_database_url:
        background_tasks.add_task(_auto_submit_job, body.session_id, all_signals, body.auth_email)

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
    auth_email: str      = Form(default=""),
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

    nudge = _missing_context_nudge(all_signals)
    if nudge and not complete:
        final_text = nudge
        quick_replies = []
        await store.append_messages(sid, [ChatMessage(role="assistant", content=final_text)])

    if complete and settings.mitra_database_url:
        background_tasks.add_task(_auto_submit_job, session_id, all_signals, auth_email or None)

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


_ACTION_MESSAGES = {
    "interested": (
        "Good news — {company} wants to connect",
        "Great news — {founder} at {company} responded to your intro for the *{role}* role "
        "and they're interested in connecting!\n\nWe'll coordinate next steps and reach out to you shortly.",
    ),
    "not_a_fit": (
        "Update on your intro to {company}",
        "{company} has reviewed your intro for the *{role}* role. "
        "They mentioned it's not the right fit at this moment — but your profile is strong "
        "and we're continuing to look for the best opportunities for you.",
    ),
    "schedule": (
        "Interview scheduled with {company}",
        "Your interview with {company} for the *{role}* role has been confirmed! "
        "The team will be in touch shortly with details.\n\nGood luck — you've got this.",
    ),
    "offer": (
        "{company} has extended you an offer",
        "Big news — {company} has extended you an offer for the *{role}* role! "
        "We'll reach out to help you navigate next steps, including any negotiation support.\n\n"
        "Congratulations — this is a big moment.",
    ),
    "hired": (
        "Congratulations — you joined {company}!",
        "Incredible news — you've officially joined {company} as *{role}*! "
        "We're so glad we could make this intro happen.\n\n"
        "Best of luck in the new role. You're going to do great.",
    ),
}


async def _notify_candidate_of_response(
    *,
    candidate_phone: str,
    candidate_name: str,
    founder_name: str,
    company: str,
    job_title: str,
    action: str,
) -> None:
    """
    Notify the candidate when a founder takes an action on their intro.
    Sends via email for web candidates (phone starts with 'web:')
    and via WhatsApp for WhatsApp candidates (plain phone number).
    """
    from mitra_api.tools.email import send_email

    subject_tpl, body_tpl = _ACTION_MESSAGES.get(action, _ACTION_MESSAGES["not_a_fit"])
    ctx = {
        "founder": founder_name or "the founder",
        "company": company,
        "role":    job_title,
    }
    subject = subject_tpl.format(**ctx) + " · Mitra"
    body    = f"Hi {candidate_name},\n\n" + body_tpl.format(**ctx) + "\n\n— Mitra"

    # ── Email delivery (web candidates) ───────────────────────────────────────
    if candidate_phone.startswith("web:"):
        candidate_email = candidate_phone.removeprefix("web:").strip()
        if "@" in candidate_email:
            try:
                await send_email(to=candidate_email, subject=subject, text=body)
            except Exception:
                log.warning("candidate email notification failed for %s (non-critical)", candidate_email)
        return

    # ── WhatsApp delivery (phone candidates) ─────────────────────────────────
    phone = candidate_phone.strip()
    if not phone:
        return
    try:
        from mitra_api.twilio_whatsapp.client import send_whatsapp_reply
        # WhatsApp body: plain text without email subject line, keep markdown bold (*..*)
        wa_body = f"Hi {candidate_name},\n\n" + body_tpl.format(**ctx) + "\n\n— Mitra"
        # Normalise to whatsapp:+XXXXXXXXXX format
        digits = "".join(c for c in phone if c.isdigit())
        wa_to  = f"whatsapp:+{digits}"
        await send_whatsapp_reply(to_whatsapp_from_value=wa_to, body=wa_body)
        log.info("candidate WA notification sent to %s action=%s", phone, action)
    except Exception:
        log.warning("candidate WA notification failed for %s action=%s (non-critical)", phone, action)


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
    company    = job.company if job else "the company"
    job_title  = job.title   if job else "the role"

    # Fire-and-forget candidate notification (email or WhatsApp)
    if candidate and candidate.phone:
        import asyncio
        asyncio.create_task(_notify_candidate_of_response(
            candidate_phone=candidate.phone,
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


# ── Founder Portal API ────────────────────────────────────────────────────────

class PortalCandidateSignals(BaseModel):
    name: str | None = None
    current_role: str | None = None
    current_company: str | None = None
    years_exp: int | None = None
    stack: list[str] = []
    salary_target_lpa: int | None = None
    notice_period_days: int | None = None
    motivation: str | None = None
    notable_projects: str | None = None
    linkedin_url: str | None = None


class PortalCandidate(BaseModel):
    intro_id: int
    status: str
    sent_at: str | None
    why_note: str | None
    signals: PortalCandidateSignals


class PortalJob(BaseModel):
    id: int
    title: str
    company: str
    stage: str | None
    sector: str | None
    location: str | None
    remote_policy: str | None
    employment: str | None
    salary_min_lpa: int | None
    salary_max_lpa: int | None
    exp_min_yrs: int | None = None
    exp_max_yrs: int | None = None
    stack: list[str]
    summary: str | None
    responsibilities: list[str] = []
    requirements: list[str] = []
    nice_to_have: list[str] = []
    company_info: dict = {}


class PortalStats(BaseModel):
    total: int
    interested: int
    interview: int
    offer: int
    hired: int
    declined: int


class PortalResponse(BaseModel):
    job: PortalJob
    candidates: list[PortalCandidate]
    stats: PortalStats


class PortalActionRequest(BaseModel):
    token: str
    intro_id: int
    action: str  # "interested" | "not_a_fit" | "schedule" | "offer" | "hired"
    interview_details: dict | None = None  # {"scheduled_at","format","link","notes"}
    offer_details: dict | None = None      # {"salary_lpa","equity_percent","start_date","notes"}
    decline_reason: str | None = None      # optional free text when action == "not_a_fit"


class PortalActionResponse(BaseModel):
    ok: bool
    new_status: str
    message: str


def _is_intro_profile_header_line(line: str) -> bool:
    """True for lines like *Name's profile:* in Mitra intro emails."""
    s = line.strip()
    return bool(s.startswith("*") and "'s profile:" in s)


def _extract_profile_block_from_intro_note(intro_note: str | None) -> str | None:
    """
    Return the bullet block under *{name}'s profile:* from the intro email body.
    This is the richest structured summary Mitra already sent the founder.
    """
    if not intro_note or not intro_note.strip():
        return None
    lines = intro_note.replace("\r\n", "\n").split("\n")
    start = -1
    for idx, line in enumerate(lines):
        if _is_intro_profile_header_line(line):
            start = idx + 1
            break
    if start < 0:
        return None
    collected: list[str] = []
    for line in lines[start:]:
        s = line.strip()
        low = s.lower()
        if s.startswith("I've spent time") or s.startswith("Would you have") or s.startswith("This isn't a spray"):
            break
        if low in {"— mitra", "- mitra"}:
            break
        if s.startswith("Quick reply") or "────────" in s:
            break
        if not s:
            continue
        collected.append(line.rstrip())
    body = "\n".join(collected).strip()
    return body or None


def _extract_why_fit_from_intro_note(intro_note: str | None) -> str | None:
    """
    Parse the LLM-authored 'why fit' paragraph(s) from a stored intro email body.

    Mitra intros use a *Why I'm making this intro:* section; the portal previously
    grabbed the first non-greeting line (often "I'd like to introduce you...").
    """
    if not intro_note or not intro_note.strip():
        return None
    t = intro_note.replace("\r\n", "\n")
    low = t.lower()

    markers = (
        "*why i'm making this intro:*",
        "*why i am making this intro:*",
    )
    start = -1
    for m in markers:
        idx = low.find(m)
        if idx != -1:
            start = idx + len(m)
            break

    if start == -1:
        plain = "why i'm making this intro:"
        idx = low.find(plain)
        if idx != -1:
            start = idx + len(plain)
        else:
            return _fallback_why_paragraph_from_intro(t)

    chunk = t[start:].lstrip("\n")
    collected: list[str] = []
    for line in chunk.split("\n"):
        stripped = line.strip()
        if not stripped:
            if collected:
                collected.append("")
            continue
        if _is_intro_profile_header_line(stripped):
            break
        if stripped.lower().startswith("*why i'm making this intro"):
            continue
        collected.append(line.rstrip())
    while collected and not collected[-1]:
        collected.pop()
    body = "\n".join(collected).strip()
    return body or _fallback_why_paragraph_from_intro(t)


def _fallback_why_paragraph_from_intro(t: str) -> str | None:
    """If section headers are missing, skip boilerplate and return first substantive line."""
    skip = (
        "hi ",
        "i'm mitra",
        "i'd like to introduce",
        "would you have",
        "i've spent time",
        "this isn't a spray",
        "— mitra",
        "quick reply",
        "────────",
    )
    for line in t.split("\n"):
        s = line.strip()
        if not s or s.startswith("─"):
            continue
        low = s.lower()
        if any(low.startswith(p) for p in skip):
            continue
        if s.startswith("*") and "profile:" in low:
            break
        if _is_intro_profile_header_line(s):
            break
        return s
    return None


def _format_portal_fit_bullets(
    signals: PortalCandidateSignals,
    raw_signals: dict[str, Any],
    job_stack: list[str],
) -> str:
    """Structured candidate facts for founders — stack, comp, location, trajectory, etc."""
    def _i(v: Any) -> int | None:
        try:
            return int(round(float(v)))
        except (TypeError, ValueError):
            return None

    js = {str(x).strip().lower() for x in job_stack if x}
    overlap = [s for s in signals.stack if str(s).strip().lower() in js]
    parts: list[str] = []
    if overlap:
        parts.append(
            f"**Stack overlap with your JD:** {', '.join(overlap)}."
        )
    elif signals.stack:
        parts.append(f"**Their stack:** {', '.join(signals.stack[:10])}.")
    if signals.years_exp is not None:
        parts.append(f"**Experience:** ~{signals.years_exp} years.")
    smin, smax = _i(raw_signals.get("salary_min_lpa")), _i(raw_signals.get("salary_max_lpa"))
    if smin and smax and smax != smin:
        parts.append(f"**Stated comp band:** ₹{smin}–{smax}L (annual).")
    elif signals.salary_target_lpa is not None:
        parts.append(f"**Comp expectation:** ₹{signals.salary_target_lpa}L target (annual).")
    ctc = _i(raw_signals.get("current_ctc_lpa"))
    if ctc:
        parts.append(f"**Current CTC (as shared):** ~₹{ctc}L.")
    if signals.current_role:
        cc = f" at *{signals.current_company}*" if signals.current_company else ""
        parts.append(f"**Current role:** {signals.current_role}{cc}.")
    if signals.notice_period_days is not None:
        parts.append(f"**Notice period:** {signals.notice_period_days} days (as shared).")

    loc = raw_signals.get("location_preference") or raw_signals.get("preferred_location") or raw_signals.get("location")
    if isinstance(loc, list):
        loc = ", ".join(str(x) for x in loc if x)
    if loc and str(loc).strip():
        parts.append(f"**Location preference:** {str(loc).strip()}.")
    rel = raw_signals.get("open_to_relocate") or raw_signals.get("relocation")
    if rel is not None and str(rel).strip() not in {"", "unknown", "Unknown"}:
        parts.append(f"**Relocation:** {str(rel).strip()}.")

    np = signals.notable_projects
    if np is not None:
        proj = str(np).strip()
        if len(proj) > 12:
            if len(proj) > 360:
                proj = proj[:357] + "…"
            parts.append(f"**Notable work / projects:** {proj}")
    if signals.motivation and len(signals.motivation) > 12:
        m = signals.motivation.strip()
        if len(m) > 400:
            m = m[:397] + "…"
        parts.append(f"**What they want next:** {m}")
    if signals.linkedin_url and str(signals.linkedin_url).strip():
        parts.append(f"**LinkedIn:** {str(signals.linkedin_url).strip()}")

    if not parts:
        return ""
    return "\n".join(f"• {p}" for p in parts)


def _format_jd_alignment_bullets(
    signals: PortalCandidateSignals,
    raw_signals: dict[str, Any],
    job_stack: list[str],
    requirements: list[str],
    nice_to_have: list[str],
    job_title: str,
) -> str:
    """Surface where the candidate lines up with this role's JD (keyword overlap)."""
    cand_parts: list[str] = []
    cand_parts.extend(str(s).lower() for s in signals.stack)
    if signals.current_role:
        cand_parts.append(str(signals.current_role).lower())
    if signals.motivation:
        cand_parts.append(signals.motivation.lower())
    mot = raw_signals.get("motivation") or raw_signals.get("what_they_want")
    if isinstance(mot, list):
        cand_parts.extend(str(m).lower() for m in mot)
    elif mot:
        cand_parts.append(str(mot).lower())
    for key in ("notable_projects", "proud_of", "built", "notable_project"):
        v = raw_signals.get(key)
        if v:
            cand_parts.append(str(v).lower())
    cand_blob = " ".join(cand_parts)

    stop = frozenset({
        "and", "the", "for", "with", "you", "our", "any", "yrs", "year", "years",
        "strong", "good", "experience", "team", "work", "ability", "skills",
    })

    def _score_req(text: str) -> bool:
        rlow = text.lower()
        tokens = re.findall(r"[a-z0-9][a-z0-9+.\-]*", rlow)
        meaningful = [w for w in tokens if len(w) > 2 and w not in stop]
        if len(meaningful) < 2:
            return any(w in cand_blob for w in meaningful)
        hits = sum(1 for w in meaningful if w in cand_blob)
        return hits >= max(1, min(2, len(meaningful) // 3))

    hits = [r.strip() for r in requirements[:12] if r and len(r.strip()) > 5 and _score_req(r)]
    parts: list[str] = []
    if hits:
        shown = hits[:3]
        more = len(hits) - len(shown)
        clips = []
        for s in shown:
            clips.append(s[:150] + ("…" if len(s) > 150 else ""))
        tail = f" (+{more} more requirements also look aligned)" if more > 0 else ""
        parts.append(f"**How they map to your requirements:** " + " · ".join(clips) + tail)

    nhits = [r.strip() for r in nice_to_have[:8] if r and len(r.strip()) > 5 and _score_req(r)]
    if nhits:
        first = nhits[0]
        parts.append(
            "**Nice-to-have fit:** "
            + (first[:130] + ("…" if len(first) > 130 else ""))
            + (f" (+{len(nhits) - 1} more)" if len(nhits) > 1 else "")
        )

    if signals.current_role and job_title:
        parts.append(f"**Trajectory:** *{signals.current_role}* → *{job_title}*.")

    js = {str(x).strip().lower() for x in job_stack if x}
    missing = [s for s in signals.stack if str(s).strip().lower() not in js][:4]
    if missing and len(job_stack) > 0:
        parts.append(
            f"**Worth probing:** Stack includes **{', '.join(missing[:3])}** — not all listed on your JD; "
            f"confirm depth in interview if critical."
        )

    if not parts:
        return ""
    return "\n".join(f"• {p}" for p in parts)


def _format_job_context_footer(
    job_title: str,
    job_location: str | None,
    job_remote_policy: str | None,
    job_salary_min: int | None,
    job_salary_max: int | None,
) -> str | None:
    bits: list[str] = []
    if job_title:
        bits.append(f"**Role:** {job_title}")
    if job_location:
        bits.append(f"**Location:** {job_location}")
    if job_remote_policy:
        pol = str(job_remote_policy).replace("_", "-")
        bits.append(f"**Work style:** {pol}")
    if job_salary_min and job_salary_max:
        bits.append(f"**Posted band:** ₹{job_salary_min}–{job_salary_max}L")
    elif job_salary_max:
        bits.append(f"**Posted up to:** ₹{job_salary_max}L")
    if not bits:
        return None
    return "**This opening (for reference):** " + " · ".join(bits) + "."


def _compose_founders_match_dossier(
    intro_note: str | None,
    signals: PortalCandidateSignals,
    raw_signals: dict[str, Any],
    *,
    job_stack: list[str],
    job_requirements: list[str],
    job_nice_to_have: list[str],
    job_title: str,
    job_location: str | None,
    job_remote_policy: str | None,
    job_salary_min: int | None,
    job_salary_max: int | None,
) -> str | None:
    """Full founder-facing 'why matched' narrative + evidence."""
    sections: list[str] = []
    why = _extract_why_fit_from_intro_note(intro_note)
    if why:
        why = normalize_why_note_for_founder(why, signals.name)
    profile = _extract_profile_block_from_intro_note(intro_note)
    if profile:
        sections.append(
            "**Snapshot from their profile** *(included in the intro email)*:\n" + profile
        )
    fit = _format_portal_fit_bullets(signals, raw_signals, job_stack)
    jd = _format_jd_alignment_bullets(
        signals, raw_signals, job_stack, job_requirements, job_nice_to_have, job_title
    )
    evidence = "\n".join(x for x in [fit, jd] if x)
    if evidence:
        sections.append("**Evidence for your decision**\n" + evidence)
    footer = _format_job_context_footer(
        job_title, job_location, job_remote_policy, job_salary_min, job_salary_max
    )
    if footer:
        sections.append(footer)
    out = "\n\n".join(s for s in sections if s).strip()
    return out or None


def _extract_portal_signals(candidate: Any, raw_signals: dict) -> PortalCandidateSignals:
    """Merge DB candidate fields + raw CandidateSignal rows into a clean struct."""
    def _int(v: Any) -> int | None:
        try: return int(v)
        except (TypeError, ValueError): return None

    def _str_list(v: Any) -> list[str]:
        if isinstance(v, list): return [str(x) for x in v]
        if isinstance(v, str) and v: return [x.strip() for x in v.split(",") if x.strip()]
        return []

    stack = (
        _str_list(raw_signals.get("primary_stack"))
        or _str_list(raw_signals.get("tech_stack"))
        or _str_list(raw_signals.get("stack"))
    )
    motivation = (
        raw_signals.get("motivation")
        or raw_signals.get("what_they_want")
        or raw_signals.get("goals")
    )
    if isinstance(motivation, list):
        motivation = "; ".join(str(m) for m in motivation)

    _np_raw = raw_signals.get("notable_projects") or raw_signals.get("proud_of") or raw_signals.get("built")
    if _np_raw is None:
        _np = None
    elif isinstance(_np_raw, str):
        _np = _np_raw.strip() or None
    else:
        _np = str(_np_raw).strip() or None

    return PortalCandidateSignals(
        name=candidate.name or raw_signals.get("candidate_name"),
        current_role=candidate.current_role or raw_signals.get("current_role"),
        current_company=candidate.current_company or raw_signals.get("current_company"),
        years_exp=candidate.years_exp or _int(raw_signals.get("years_experience")),
        stack=stack,
        salary_target_lpa=_int(raw_signals.get("salary_target_lpa") or raw_signals.get("salary_floor_lpa")),
        notice_period_days=_int(raw_signals.get("notice_period_days") or raw_signals.get("notice_period")),
        motivation=str(motivation).strip() if motivation else None,
        notable_projects=_np,
        linkedin_url=raw_signals.get("linkedin_url") or raw_signals.get("linkedin"),
    )


class PortalLinkResponse(BaseModel):
    portal_url: str
    job_id: int | None = None


class FounderJobSummary(BaseModel):
    job_id: int
    title: str
    company: str
    stage: str | None = None
    portal_url: str
    total_intros: int = 0
    to_review: int = 0   # sent + acknowledged — awaiting founder action


class AllPortalsResponse(BaseModel):
    jobs: list[FounderJobSummary]


@router.get("/all-portals-by-email", response_model=AllPortalsResponse)
async def founder_all_portals_by_email(
    email: str = Query(..., description="Founder email address from auth session"),
) -> AllPortalsResponse:
    """
    Return all jobs (and their portal URLs) for a given founder email.
    Includes intro counts so the role picker can show "N to review" badges.
    Used by /founder/setup to display a role picker when the founder has multiple roles.
    """
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job as JobModel
    from sqlalchemy import String, func

    normalized_email = email.strip().lower()
    factory = get_session_factory()

    async with factory() as db:
        # Primary match: founder_email column
        jobs = (await db.execute(
            select(JobModel)
            .where(
                func.lower(JobModel.founder_email) == normalized_email,
                JobModel.founder_access_token.isnot(None),
            )
            .order_by(JobModel.created_at.desc())
        )).scalars().all()

        if not jobs:
            # Fallback: founder_wa field (sometimes email is stored there)
            jobs = (await db.execute(
                select(JobModel)
                .where(
                    func.lower(JobModel.founder_wa) == normalized_email,
                    JobModel.founder_access_token.isnot(None),
                )
                .order_by(JobModel.created_at.desc())
            )).scalars().all()

        if not jobs:
            # Final fallback: scan signals JSONB for the email string
            jobs = (await db.execute(
                select(JobModel)
                .where(
                    JobModel.founder_access_token.isnot(None),
                    JobModel.signals.cast(String).ilike(f"%{normalized_email}%"),
                )
                .order_by(JobModel.created_at.desc())
            )).scalars().all()

        # Count intros per job in the same session
        total_map: dict[int, int] = {}
        review_map: dict[int, int] = {}
        if jobs:
            from mitra_api.db.models import Intro
            job_ids = [j.id for j in jobs if j.founder_access_token]
            intro_rows = (await db.execute(
                select(Intro.job_id, Intro.status).where(Intro.job_id.in_(job_ids))
            )).all()
            review_statuses = {"sent", "acknowledged"}
            for row in intro_rows:
                total_map[row.job_id] = total_map.get(row.job_id, 0) + 1
                status_val = row.status.value if hasattr(row.status, "value") else str(row.status)
                if status_val in review_statuses:
                    review_map[row.job_id] = review_map.get(row.job_id, 0) + 1

    settings = get_settings()
    web_base = settings.mitra_web_base_url.rstrip("/")

    result = [
        FounderJobSummary(
            job_id=j.id,
            title=j.title or "Untitled role",
            company=j.company or "Your company",
            stage=j.stage,
            portal_url=f"{web_base}/founder/portal?token={j.founder_access_token}",
            total_intros=total_map.get(j.id, 0),
            to_review=review_map.get(j.id, 0),
        )
        for j in jobs
        if j.founder_access_token
    ]

    return AllPortalsResponse(jobs=result)


@router.get("/portal-link-by-email", response_model=PortalLinkResponse)
async def founder_portal_link_by_email(
    email: str = Query(..., description="Founder email address from auth session"),
) -> PortalLinkResponse:
    """
    Look up a founder's portal URL by their email address.
    Called from /founder/setup after OAuth sign-in to find an existing job.
    Matches against founder_email column OR the contact_info signal stored on job.signals.
    """
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job as JobModel
    from sqlalchemy import String, func

    normalized_email = email.strip().lower()

    factory = get_session_factory()
    async with factory() as db:
        # Case-insensitive match on founder_email
        job = (await db.execute(
            select(JobModel)
            .where(
                func.lower(JobModel.founder_email) == normalized_email,
                JobModel.founder_access_token.isnot(None),
            )
            .order_by(JobModel.created_at.desc())
        )).scalars().first()

        # Fallback: scan founder_wa (in case they used email as WA field by mistake)
        if not job:
            job = (await db.execute(
                select(JobModel)
                .where(
                    func.lower(JobModel.founder_wa) == normalized_email,
                    JobModel.founder_access_token.isnot(None),
                )
                .order_by(JobModel.created_at.desc())
            )).scalars().first()

        # Final fallback: scan signals JSONB text for the email
        if not job:
            job = (await db.execute(
                select(JobModel)
                .where(
                    JobModel.founder_access_token.isnot(None),
                    JobModel.signals.cast(String).ilike(f"%{normalized_email}%"),
                )
                .order_by(JobModel.created_at.desc())
            )).scalars().first()

    if not job or not job.founder_access_token:
        raise HTTPException(status_code=404, detail="no_job_found")

    settings = get_settings()
    web_base = settings.mitra_web_base_url.rstrip("/")
    portal_url = f"{web_base}/founder/portal?token={job.founder_access_token}"
    return PortalLinkResponse(portal_url=portal_url, job_id=job.id)


@router.get("/portal-link", response_model=PortalLinkResponse)
async def founder_portal_link(
    session_id: str = Query(..., description="Founder session ID from onboarding"),
) -> PortalLinkResponse:
    """
    Return the portal URL for a founder session.
    Called by the onboarding frontend after completion so the founder can
    access their portal without any manual steps.
    """
    from mitra_api.config import get_settings
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job as JobModel

    external_id = f"founder:{session_id}"
    factory = get_session_factory()
    async with factory() as db:
        job = (await db.execute(
            select(JobModel).where(JobModel.external_id == external_id)
        )).scalar_one_or_none()

    if not job or not job.founder_access_token:
        raise HTTPException(
            status_code=404,
            detail="Job not found. The onboarding may still be processing — try again in a moment.",
        )

    web_base = get_settings().mitra_web_base_url.rstrip("/")
    portal_url = f"{web_base}/founder/portal?token={job.founder_access_token}"
    return PortalLinkResponse(portal_url=portal_url, job_id=job.id)


_GHOST_AFTER_DAYS = 7


@router.get("/portal", response_model=PortalResponse)
async def founder_portal(
    token: str = Query(..., description="Founder access token from intro email"),
) -> PortalResponse:
    """Return job details + all introduced candidates for this founder's role."""
    from datetime import datetime, timedelta, timezone
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job as JobModel, Intro, IntroStatus, Candidate, CandidateSignal

    factory = get_session_factory()
    async with factory() as db:
        job = (await db.execute(
            select(JobModel).where(JobModel.founder_access_token == token)
        )).scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="Portal not found or token expired.")

        # Auto-ghost stale intros that never got a founder response
        ghost_cutoff = datetime.now(timezone.utc) - timedelta(days=_GHOST_AFTER_DAYS)
        stale = (await db.execute(
            select(Intro).where(
                Intro.job_id == job.id,
                Intro.status == IntroStatus.sent,
                Intro.sent_at <= ghost_cutoff,
            )
        )).scalars().all()
        if stale:
            for intro in stale:
                intro.status     = IntroStatus.ghosted
                intro.updated_at = datetime.now(timezone.utc)
            await db.commit()
            log.info("auto-ghosted %d stale intro(s) for job=%d", len(stale), job.id)

        job_sigs: dict = job.signals if isinstance(job.signals, dict) else {}

        def _job_list(v: Any) -> list[str]:
            if isinstance(v, list):
                return [str(x) for x in v if x]
            return []

        job_requirements = _job_list(job_sigs.get("requirements"))
        job_nice_to_have = _job_list(job_sigs.get("nice_to_have"))

        # Load all intros for this job with candidates
        rows = (await db.execute(
            select(Intro, Candidate)
            .join(Candidate, Intro.candidate_id == Candidate.id)
            .where(Intro.job_id == job.id)
            .order_by(Intro.sent_at.desc())
        )).all()

        candidates_out: list[PortalCandidate] = []
        for intro, candidate in rows:
            # Load candidate signals
            sig_rows = (await db.execute(
                select(CandidateSignal).where(CandidateSignal.candidate_id == candidate.id)
            )).scalars().all()
            raw_signals = {r.key: r.value for r in sig_rows}
            signals = _extract_portal_signals(candidate, raw_signals)

            job_stack_list = [str(s) for s in job.stack] if isinstance(job.stack, list) else []
            why_note = _compose_founders_match_dossier(
                intro.intro_note,
                signals,
                raw_signals,
                job_stack=job_stack_list,
                job_requirements=job_requirements,
                job_nice_to_have=job_nice_to_have,
                job_title=job.title or "",
                job_location=job.location,
                job_remote_policy=job.remote_policy,
                job_salary_min=job.salary_min_lpa,
                job_salary_max=job.salary_max_lpa,
            )

            candidates_out.append(PortalCandidate(
                intro_id=intro.id,
                status=intro.status.value if hasattr(intro.status, "value") else str(intro.status),
                sent_at=intro.sent_at.isoformat() if intro.sent_at else None,
                why_note=why_note,
                signals=signals,
            ))

    stats = PortalStats(
        total=len(candidates_out),
        interested=sum(1 for c in candidates_out if c.status == "acknowledged"),
        interview=sum(1 for c in candidates_out if c.status == "interview"),
        offer=sum(1 for c in candidates_out if c.status == "offer"),
        hired=sum(1 for c in candidates_out if c.status == "hired"),
        declined=sum(1 for c in candidates_out if c.status == "declined"),
    )

    # Pull extra fields stored in signals JSONB by the job builder
    sigs: dict = job.signals if isinstance(job.signals, dict) else {}

    def _str_list(v: Any) -> list[str]:
        if isinstance(v, list): return [str(x) for x in v if x]
        return []

    job_out = PortalJob(
        id=job.id,
        title=job.title,
        company=job.company,
        stage=job.stage,
        sector=job.sector,
        location=job.location,
        remote_policy=job.remote_policy,
        employment=job.employment,
        salary_min_lpa=job.salary_min_lpa,
        salary_max_lpa=job.salary_max_lpa,
        exp_min_yrs=sigs.get("exp_min_yrs"),
        exp_max_yrs=sigs.get("exp_max_yrs"),
        stack=[str(s) for s in job.stack] if isinstance(job.stack, list) else [],
        summary=job.summary,
        responsibilities=_str_list(sigs.get("responsibilities")),
        requirements=_str_list(sigs.get("requirements")),
        nice_to_have=_str_list(sigs.get("nice_to_have")),
        company_info=sigs.get("company_info") if isinstance(sigs.get("company_info"), dict) else {},
    )

    return PortalResponse(job=job_out, candidates=candidates_out, stats=stats)


@router.post("/portal/action", response_model=PortalActionResponse)
async def founder_portal_action(body: PortalActionRequest) -> PortalActionResponse:
    """Update intro status from the founder portal."""
    from datetime import datetime, timezone
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job as JobModel, Intro, Candidate, IntroStatus

    action_map = {
        "interested": IntroStatus.acknowledged,
        "not_a_fit":  IntroStatus.declined,
        "schedule":   IntroStatus.interview,
        "offer":      IntroStatus.offer,
        "hired":      IntroStatus.hired,
    }
    if body.action not in action_map:
        raise HTTPException(400, f"Invalid action '{body.action}'. Use: interested, not_a_fit, schedule, offer, hired.")

    from mitra_api.db.models import Match

    factory = get_session_factory()
    async with factory() as db:
        # Verify the token owns this intro
        job = (await db.execute(
            select(JobModel).where(JobModel.founder_access_token == body.token)
        )).scalar_one_or_none()

        if not job:
            raise HTTPException(404, "Portal not found or token expired.")

        intro = (await db.execute(
            select(Intro).where(Intro.id == body.intro_id, Intro.job_id == job.id)
        )).scalar_one_or_none()

        if not intro:
            raise HTTPException(404, "Candidate not found in this portal.")

        # Skip if already in a terminal state
        terminal = {IntroStatus.hired, IntroStatus.declined}
        current_status = intro.status.value if hasattr(intro.status, "value") else str(intro.status)
        if current_status in {s.value for s in terminal} and body.action == "not_a_fit":
            return PortalActionResponse(ok=True, new_status=current_status, message="Already actioned.")

        new_status = action_map[body.action]
        now = datetime.now(timezone.utc)
        intro.status     = new_status
        intro.updated_at = now
        # Set stage timestamp on first transition into each state
        if body.action == "schedule":
            if intro.interview_at is None:
                intro.interview_at = now
            if body.interview_details:
                intro.interview_details = body.interview_details
        elif body.action == "offer":
            if intro.offer_at is None:
                intro.offer_at = now
            if body.offer_details:
                intro.offer_details = body.offer_details
        elif body.action == "hired" and intro.hired_at is None:
            intro.hired_at = now
        elif body.action == "not_a_fit" and body.decline_reason:
            intro.decline_reason = body.decline_reason.strip()
        # Consume response_token (same link should not double-trigger)
        if intro.response_token:
            intro.response_token = None

        # Sync outcome back to matches table for learning
        match_row = (await db.execute(
            select(Match).where(Match.intro_id == intro.id)
        )).scalar_one_or_none()
        if match_row:
            match_row.founder_action   = body.action
            match_row.founder_feedback = body.decline_reason.strip() if body.decline_reason else None
            match_row.decided_at       = now

        # Update founder behavioural profile — learns response velocity and candidate preferences
        try:
            from mitra_api.db.models import CandidateSignal
            from mitra_api.tools.intelligence import update_founder_response_pattern
            sig_rows = (await db.execute(
                select(CandidateSignal).where(CandidateSignal.candidate_id == intro.candidate_id)
            )).scalars().all()
            candidate_signals_for_learning: dict = {r.key: r.value for r in sig_rows}

            response_hours: float | None = None
            if intro.sent_at:
                delta = now - intro.sent_at
                response_hours = delta.total_seconds() / 3600

            responded = body.action in ("interested", "schedule", "offer", "hired")
            existing_profile = (
                job.signals.get("_founder_profile", {})
                if isinstance(job.signals, dict) else {}
            )
            updated_profile = update_founder_response_pattern(
                existing_profile,
                responded=responded,
                response_hours=response_hours if responded else None,
                candidate_signals=candidate_signals_for_learning,
                passed_reason=body.decline_reason if body.action == "not_a_fit" else None,
            )
            new_job_signals = dict(job.signals) if isinstance(job.signals, dict) else {}
            new_job_signals["_founder_profile"] = updated_profile
            job.signals = new_job_signals
            log.info(
                "founder profile updated: job=%d action=%s response_rate=%.0f%%",
                job.id, body.action,
                updated_profile.get("response_rate_pct", 0),
            )
        except Exception:
            log.debug("founder pattern learning failed (non-critical)")

        await db.commit()

        # Notify candidate asynchronously
        candidate = (await db.execute(
            select(Candidate).where(Candidate.id == intro.candidate_id)
        )).scalar_one_or_none()

    cand_name = (candidate.name or "there") if candidate else "there"

    if candidate and candidate.phone:
        import asyncio
        asyncio.create_task(_notify_candidate_of_response(
            candidate_phone=candidate.phone,
            candidate_name=cand_name,
            founder_name=job.founder_name or "",
            company=job.company,
            job_title=job.title,
            action=body.action,
        ))

    status_messages = {
        "interested": f"Marked as interested — {cand_name} will be notified.",
        "not_a_fit":  f"Noted. {cand_name} has been informed respectfully.",
        "schedule":   f"Interview stage set — we'll coordinate with {cand_name}.",
        "offer":      f"Offer extended — {cand_name} has been notified. Exciting!",
        "hired":      f"Congratulations! {cand_name} is now marked as hired.",
    }

    log.info("portal action: job=%d intro=%d action=%s", job.id, intro.id, body.action)
    return PortalActionResponse(
        ok=True,
        new_status=new_status.value if hasattr(new_status, "value") else str(new_status),
        message=status_messages[body.action],
    )


class DeleteJobRequest(BaseModel):
    token: str


class DeleteJobResponse(BaseModel):
    ok: bool
    message: str


@router.delete("/portal/job", response_model=DeleteJobResponse)
async def founder_delete_job(body: DeleteJobRequest) -> DeleteJobResponse:
    """
    Hard-delete a founder's job and all related records (intros, embedding).
    The Job model has cascade="all, delete-orphan" on both relationships,
    so a single db.delete(job) removes everything cleanly.
    """
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job as JobModel

    factory = get_session_factory()
    async with factory() as db:
        job = (await db.execute(
            select(JobModel).where(JobModel.founder_access_token == body.token)
        )).scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="Portal not found or token expired.")

        job_title   = job.title or "Untitled role"
        job_company = job.company or "your company"
        job_id      = job.id

        await db.delete(job)
        await db.commit()

    log.info("founder hard-deleted job=%d ('%s' @ %s) via portal", job_id, job_title, job_company)
    return DeleteJobResponse(ok=True, message=f"'{job_title}' at {job_company} has been permanently deleted.")
