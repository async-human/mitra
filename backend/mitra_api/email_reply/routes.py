"""
mitra_api/email_reply/routes.py

POST /webhook/email-reply

Receives inbound emails forwarded by the Cloudflare Email Worker.
Identifies conversation context from the reply token embedded in the
reply-to address (reply+TOKEN@mitralabs.co), then routes:

  Candidate reply -> run_agent_turn -> respond via email
  Founder reply   -> LLM intent classification -> update intro status -> respond
  Unknown token   -> forward raw email to ops inbox
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

router = APIRouter()

# ── FOUNDER INTENT PROMPT ─────────────────────────────────────────────────────

_INTENT_SYSTEM = """You are classifying a founder's email reply to a candidate introduction from Mitra, a recruiting agent.

Classify the reply intent as exactly one of these labels:
- interested   : founder likes the candidate and wants to proceed
- scheduling   : founder is trying to book a call or interview
- passing      : founder is declining / candidate is not the right fit
- asking_more  : founder wants more information about the candidate
- other        : anything else

Reply with ONLY the single label. No explanation."""

_DECLINE_REASON_SYSTEM = """Extract the founder's reason for declining a candidate from their email reply.
Return a single concise sentence (max 20 words) capturing the core reason.
Examples: "Not enough backend experience", "Looking for a senior IC not a manager", "Already hired someone", "Salary expectations too high".
If no clear reason is stated, return an empty string.
Reply with ONLY the extracted reason or empty string — no explanation."""

_FOUNDER_RESPONSES: dict[str, str] = {
    "interested": (
        "Great to hear — I'll let the candidate know you're interested.\n\n"
        "Feel free to reach out to them directly, or reply here if you'd like "
        "me to help coordinate next steps.\n\n— Mitra"
    ),
    "scheduling": (
        "Perfect — I've noted that you're looking to schedule a conversation.\n\n"
        "I'll let the candidate know to expect your message. Feel free to loop "
        "me in if you need anything from my side.\n\n— Mitra"
    ),
    "passing": (
        "Understood — thanks for letting me know. Your feedback helps me calibrate "
        "future introductions.\n\n"
        "I'll keep the search active and be in touch when I find a better fit.\n\n— Mitra"
    ),
    "asking_more": (
        "Happy to share more detail. Could you let me know what would be most useful — "
        "a specific technology, a past project example, or something about their background?\n\n"
        "I'll get you what you need.\n\n— Mitra"
    ),
    "other": (
        "Thanks for your message — I'll follow up shortly.\n\n— Mitra"
    ),
}


# ── WEBHOOK ───────────────────────────────────────────────────────────────────

@router.post("/webhook/email-reply")
async def receive_email_reply(
    request: Request,
    x_email_secret: str = Header(default=""),
) -> JSONResponse:
    from mitra_api.config import get_settings
    s = get_settings()

    expected = (getattr(s, "email_webhook_secret", "") or "").strip()
    if expected and x_email_secret != expected:
        raise HTTPException(403, "Invalid email webhook secret")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    from_addr  = (body.get("from") or "").strip()
    to_addr    = (body.get("to")   or "").strip()
    token      = body.get("token")
    raw_email  = body.get("raw_email", "")
    subject    = (body.get("subject") or "").strip()

    from mitra_api.email_reply.parser import extract_reply_text
    reply_text = extract_reply_text(raw_email)

    if not reply_text.strip():
        log.info("email-reply: empty body from %s — skipping", from_addr)
        return JSONResponse({"status": "skipped", "reason": "empty body"})

    log.info(
        "email-reply: from=%s to=%s token=%s body_len=%d",
        from_addr, to_addr, token, len(reply_text),
    )

    # ── Resolve context from token ────────────────────────────────────────────
    context: dict[str, Any] | None = None
    if token:
        from mitra_api.email_reply.token_store import get_reply_context
        context = await get_reply_context(token)

    if not context:
        await _forward_to_ops(from_addr, to_addr, reply_text, s)
        return JSONResponse({"status": "forwarded_to_ops"})

    reply_type = context.get("type")

    if reply_type == "candidate":
        await _handle_candidate_reply(
            from_email=from_addr,
            session_id=context.get("session_id", from_addr),
            reply_text=reply_text,
            subject=subject,
        )
    elif reply_type == "founder":
        await _handle_founder_reply(
            from_email=from_addr,
            intro_id=context.get("intro_id"),
            job_id=context.get("job_id"),
            reply_text=reply_text,
        )
    else:
        log.warning("email-reply: unknown context type=%s", reply_type)

    return JSONResponse({"status": "ok", "type": reply_type})


# ── CANDIDATE HANDLER ─────────────────────────────────────────────────────────

async def _handle_candidate_reply(
    *,
    from_email: str,
    session_id: str,
    reply_text: str,
    subject: str,
) -> None:
    """Feed the email reply into the agent turn and respond via email."""
    try:
        from mitra_api.agent.orchestrator import run_agent_turn
        from mitra_api.agent.session_store import build_session_store
        from mitra_api.config import get_settings
        from mitra_api.tools.email import send_email

        s     = get_settings()
        store = build_session_store(s)

        turn = await run_agent_turn(
            whatsapp_sender_id=session_id,
            user_text=reply_text,
            sessions=store,
            settings=s,
        )

        response_text = turn.history_assistant_text
        if not response_text:
            log.warning("email-reply: agent returned empty response for %s", from_email)
            return

        reply_subject = (
            f"Re: {subject}"
            if subject and not subject.lower().startswith("re:")
            else (subject or "From Mitra")
        )

        await send_email(
            to=from_email,
            subject=reply_subject,
            text=response_text,
            reply_context={"type": "candidate", "session_id": session_id},
        )
        log.info("email-reply: candidate response sent to %s", from_email)

    except Exception:
        log.exception("email-reply: candidate handler failed for %s", from_email)


# ── FOUNDER HANDLER ───────────────────────────────────────────────────────────

async def _handle_founder_reply(
    *,
    from_email: str,
    intro_id: int | None,
    job_id: int | None,
    reply_text: str,
) -> None:
    """Classify founder intent, update intro status, and respond."""
    try:
        from mitra_api.config import get_settings
        from mitra_api.llm.factory import get_llm_adapter
        from mitra_api.llm.types import ChatMessage
        from mitra_api.tools.email import send_email

        s       = get_settings()
        adapter = get_llm_adapter(s)

        result = await adapter.complete(
            model=s.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_INTENT_SYSTEM),
                ChatMessage(role="user",   content=reply_text[:1000]),
            ],
            tools=[],
            max_tokens=10,
            temperature=0.0,
        )
        intent = (result.content or "other").strip().lower()
        log.info("email-reply: founder intent=%s intro_id=%s", intent, intro_id)

        # Update intro status in DB (pass reply_text for decline reason extraction)
        if intro_id:
            await _update_intro_from_intent(intro_id, intent, reply_text=reply_text[:800])

        # Respond to founder
        response = _FOUNDER_RESPONSES.get(intent, _FOUNDER_RESPONSES["other"])
        await send_email(
            to=from_email,
            subject="Re: Candidate Introduction — Mitra",
            text=response,
            reply_context={"type": "founder", "intro_id": intro_id, "job_id": job_id},
        )
        log.info("email-reply: founder response sent to %s (intent=%s)", from_email, intent)

    except Exception:
        log.exception("email-reply: founder handler failed for %s", from_email)


async def _extract_decline_reason(reply_text: str) -> str:
    """Use LLM to pull a concise decline reason from the founder's email."""
    try:
        from mitra_api.config import get_settings
        from mitra_api.llm.factory import get_llm_adapter
        from mitra_api.llm.types import ChatMessage
        s = get_settings()
        adapter = get_llm_adapter(s)
        result = await adapter.complete(
            model=s.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_DECLINE_REASON_SYSTEM),
                ChatMessage(role="user",   content=reply_text[:800]),
            ],
            tools=[],
            max_tokens=40,
            temperature=0.0,
        )
        return (result.content or "").strip()
    except Exception:
        log.debug("decline reason extraction failed (non-critical)")
        return ""


async def _update_intro_from_intent(intro_id: int, intent: str, reply_text: str = "") -> None:
    """Map founder intent to an IntroStatus, capture decline reason, and persist."""
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Intro, IntroStatus, Match
    from sqlalchemy import select

    status_map = {
        "interested": IntroStatus.acknowledged,
        "scheduling": IntroStatus.interview,
        "passing":    IntroStatus.declined,
    }
    new_status = status_map.get(intent)
    if not new_status:
        return

    decline_reason = ""
    if intent == "passing" and reply_text:
        decline_reason = await _extract_decline_reason(reply_text)

    try:
        now = datetime.now(timezone.utc)
        factory = get_session_factory()
        async with factory() as db:
            row = (await db.execute(
                select(Intro).where(Intro.id == intro_id)
            )).scalar_one_or_none()

            if row:
                row.status     = new_status
                row.updated_at = now
                if new_status == IntroStatus.interview:
                    row.interview_at = now
                if decline_reason:
                    row.decline_reason = decline_reason

                # Sync outcome to matches table
                match_row = (await db.execute(
                    select(Match).where(Match.intro_id == intro_id)
                )).scalar_one_or_none()
                if match_row:
                    match_row.founder_action   = intent
                    match_row.founder_feedback = decline_reason or None
                    match_row.decided_at       = now

                await db.commit()
                log.info(
                    "intro %d status→%s decline_reason=%r",
                    intro_id, new_status, decline_reason or "(none)",
                )
    except Exception:
        log.exception("_update_intro_from_intent failed for intro_id=%d", intro_id)


# ── FALLBACK ──────────────────────────────────────────────────────────────────

async def _forward_to_ops(
    from_addr: str,
    to_addr: str,
    reply_text: str,
    s: Any,
) -> None:
    ops = (getattr(s, "mitra_ops_email", "") or "").strip()
    if not ops:
        log.warning("email-reply: no token match and no ops email configured")
        return

    from mitra_api.tools.email import send_email
    await send_email(
        to=ops,
        subject=f"[Unmatched email reply] from {from_addr}",
        text=f"From: {from_addr}\nTo: {to_addr}\n\n{reply_text}",
    )
    log.info("email-reply: unmatched reply forwarded to ops (%s)", ops)
