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

_SLOT_EXTRACT_SYSTEM = """Extract specific time slot offers from the text.
Return a short clean list like "Tuesday 2pm–3pm, Thursday 11am, Friday morning".
If no specific times are mentioned, return an empty string.
Reply with ONLY the formatted time slots or empty string — no explanation."""

_SLOT_CONFIRM_SYSTEM = """The user is confirming a specific time slot from a list they were given.
Extract the single slot they confirmed, e.g. "Tuesday 2pm" or "Thursday 11am".
If they are asking a question or not confirming a specific slot, return "pending".
Reply with ONLY the confirmed slot or "pending" — no explanation."""

_FOUNDER_RESPONSES: dict[str, str] = {
    "interested": (
        "Great to hear — I'll let the candidate know you're interested.\n\n"
        "Feel free to reach out to them directly, or reply here if you'd like "
        "me to help coordinate next steps.\n\n— Mitra"
    ),
    # "scheduling" is handled actively — no canned response used
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
            context=context,
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


# ── SCHEDULING HELPERS ────────────────────────────────────────────────────────

async def _extract_time_slots(text: str) -> str:
    """Extract time slot offers from natural language. Returns formatted string or ''."""
    try:
        from mitra_api.config import get_settings
        from mitra_api.llm.factory import get_llm_adapter
        from mitra_api.llm.types import ChatMessage
        s       = get_settings()
        adapter = get_llm_adapter(s)
        result  = await adapter.complete(
            model=s.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_SLOT_EXTRACT_SYSTEM),
                ChatMessage(role="user",   content=text[:600]),
            ],
            tools=[],
            max_tokens=80,
            temperature=0.0,
        )
        return (result.content or "").strip()
    except Exception:
        log.debug("slot extraction failed (non-critical)")
        return ""


async def _extract_slot_confirmation(text: str) -> str:
    """
    Determine which slot the candidate confirmed from a list they were given.
    Returns the confirmed slot string, or 'pending' if none confirmed yet.
    """
    try:
        from mitra_api.config import get_settings
        from mitra_api.llm.factory import get_llm_adapter
        from mitra_api.llm.types import ChatMessage
        s       = get_settings()
        adapter = get_llm_adapter(s)
        result  = await adapter.complete(
            model=s.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_SLOT_CONFIRM_SYSTEM),
                ChatMessage(role="user",   content=text[:400]),
            ],
            tools=[],
            max_tokens=30,
            temperature=0.0,
        )
        return (result.content or "pending").strip()
    except Exception:
        log.debug("slot confirmation extraction failed (non-critical)")
        return "pending"


async def _get_intro_contacts(intro_id: int) -> dict:
    """Fetch candidate + founder contact details and job info for a given intro."""
    try:
        from mitra_api.db.engine import get_session_factory
        from mitra_api.db.models import Candidate, Intro, Job
        from sqlalchemy import select
        factory = get_session_factory()
        async with factory() as db:
            row = (await db.execute(
                select(Intro, Candidate, Job)
                .join(Candidate, Intro.candidate_id == Candidate.id)
                .join(Job,       Intro.job_id       == Job.id)
                .where(Intro.id == intro_id)
            )).first()
        if not row:
            return {}
        intro, candidate, job = row
        phone      = candidate.phone or ""
        is_web     = phone.startswith("web:")
        cand_email = phone[4:] if is_web else None
        return {
            "candidate_name":  candidate.name or "there",
            "candidate_phone": phone,
            "candidate_email": cand_email,
            "candidate_first": (candidate.name or "there").split()[0],
            "founder_name":    job.founder_name or "there",
            "founder_email":   job.founder_email,
            "founder_wa":      job.founder_wa,
            "job_title":       job.title,
            "company":         job.company,
        }
    except Exception:
        log.exception("_get_intro_contacts failed for intro_id=%d", intro_id)
        return {}


async def _confirm_interview(
    intro_id: int,
    confirmed_slot: str,
    contacts: dict,
) -> None:
    """
    Lock in a confirmed interview slot:
    - Email both sides with the confirmed time
    - Update intro status to interview with details stored
    """
    from mitra_api.tools.email import send_email
    from datetime import datetime, timezone

    cand_first  = contacts.get("candidate_first", "there")
    founder     = contacts.get("founder_name", "there")
    company     = contacts.get("company", "the company")
    role        = contacts.get("job_title", "the role")
    cand_email  = contacts.get("candidate_email")
    found_email = contacts.get("founder_email")

    # Email the candidate
    if cand_email:
        await send_email(
            to=cand_email,
            subject=f"Confirmed: your call with {company} — {confirmed_slot}",
            text=(
                f"Hey {cand_first}!\n\n"
                f"You're all set. Your 30-minute call with {company} for the {role} role "
                f"is confirmed for {confirmed_slot}.\n\n"
                f"The founder will reach out with a calendar invite or call link. "
                f"Feel free to reply here if anything changes.\n\n"
                f"Good luck — rooting for you!\n\n— Mitra"
            ),
            reply_context={"type": "candidate", "session_id": contacts.get("candidate_phone", ""), "intro_id": intro_id},
        )

    # Email the founder
    if found_email:
        await send_email(
            to=found_email,
            subject=f"Confirmed: {contacts.get('candidate_name', 'Candidate')} — {confirmed_slot}",
            text=(
                f"Hi {founder},\n\n"
                f"{contacts.get('candidate_name', 'The candidate')} has confirmed "
                f"{confirmed_slot} for a 30-minute call about the {role} role.\n\n"
                f"Please send them a calendar invite or call link at your earliest convenience.\n\n"
                f"I'll check in after the interview to see how it went.\n\n— Mitra"
            ),
            reply_context={"type": "founder", "intro_id": intro_id},
        )

    # Update intro in DB
    try:
        from mitra_api.db.engine import get_session_factory
        from mitra_api.db.models import Intro, IntroStatus
        from sqlalchemy import select
        now = datetime.now(timezone.utc)
        factory = get_session_factory()
        async with factory() as db:
            row = (await db.execute(
                select(Intro).where(Intro.id == intro_id)
            )).scalar_one_or_none()
            if row:
                row.status         = IntroStatus.interview
                row.interview_at   = now
                row.updated_at     = now
                row.interview_details = {
                    "scheduled_at": confirmed_slot,
                    "format":       "call",
                    "notes":        "Coordinated by Mitra via email",
                }
                await db.commit()
                log.info("intro %d → interview confirmed at %s", intro_id, confirmed_slot)
    except Exception:
        log.exception("_confirm_interview: DB update failed for intro_id=%d", intro_id)


# ── CANDIDATE HANDLER ─────────────────────────────────────────────────────────

async def _handle_candidate_reply(
    *,
    from_email: str,
    session_id: str,
    reply_text: str,
    subject: str,
    context: dict | None = None,
) -> None:
    """
    Route the candidate's email reply.
    - If this is a scheduling context (replying to slot offer): extract confirmation
      and lock in the interview if a slot is confirmed.
    - Otherwise: feed into the agent turn and respond conversationally.
    """
    context = context or {}
    try:
        from mitra_api.tools.email import send_email

        # ── Scheduling confirmation path ──────────────────────────────────────
        if context.get("scheduling") and context.get("intro_id"):
            intro_id      = context["intro_id"]
            founder_slots = context.get("founder_slots", "")
            confirmed     = await _extract_slot_confirmation(reply_text)

            if confirmed and confirmed != "pending":
                contacts = await _get_intro_contacts(intro_id)
                await _confirm_interview(intro_id, confirmed, contacts)
                log.info(
                    "email-reply: scheduling confirmed intro=%d slot=%s candidate=%s",
                    intro_id, confirmed, from_email,
                )
                return

            # Candidate asked a question or wasn't sure — fall through to agent
            # but inject scheduling context into the message
            if founder_slots:
                reply_text = (
                    f"[Re scheduling with the founder — available slots: {founder_slots}]\n\n"
                    + reply_text
                )

        # ── Normal agent turn path ────────────────────────────────────────────
        from mitra_api.agent.orchestrator import run_agent_turn
        from mitra_api.agent.session_store import build_session_store
        from mitra_api.config import get_settings

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
            reply_context={
                "type":       "candidate",
                "session_id": session_id,
                **({"intro_id": context["intro_id"], "scheduling": True} if context.get("scheduling") else {}),
            },
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

        # ── Scheduling intent ─────────────────────────────────────────────────
        if intent == "scheduling" and intro_id:
            from mitra_api.config import get_settings as _gs
            from mitra_api.tools.cal import build_booking_link
            _s = _gs()
            contacts = await _get_intro_contacts(intro_id)

            # If Cal.com is configured, the candidate already has a booking link —
            # just reassure the founder and let Cal.com handle the rest.
            if _s.cal_booking_url:
                cand_name  = contacts.get("candidate_name", "the candidate")
                founder    = contacts.get("founder_name", "there")
                await send_email(
                    to=from_email,
                    subject="Re: Candidate Introduction — Mitra",
                    text=(
                        f"Hi {founder},\n\n"
                        f"I've already sent {cand_name} a link to book a time "
                        f"directly via your Cal.com calendar. You'll receive a "
                        f"calendar invite as soon as they pick a slot — usually "
                        f"within a few hours.\n\n— Mitra"
                    ),
                    reply_context={"type": "founder", "intro_id": intro_id, "job_id": job_id},
                )
                return

            # No Cal.com — fall through to manual slot extraction below
            slots    = await _extract_time_slots(reply_text)
            contacts = await _get_intro_contacts(intro_id)

            cand_first  = contacts.get("candidate_first", "the candidate")
            cand_name   = contacts.get("candidate_name", "the candidate")
            cand_email  = contacts.get("candidate_email")
            cand_phone  = contacts.get("candidate_phone", "")
            company     = contacts.get("company", "the company")
            role        = contacts.get("job_title", "the role")
            founder     = contacts.get("founder_name", "there")

            if slots and cand_email:
                # Forward availability to candidate and ask them to confirm a slot
                await send_email(
                    to=cand_email,
                    subject=f"Confirming your call with {company} — {role}",
                    text=(
                        f"Hey {cand_first}!\n\n"
                        f"Great news — the founder at {company} is available:\n\n"
                        f"  {slots}\n\n"
                        f"Which of these works for you? Reply with your preferred slot "
                        f"and I'll confirm with them immediately.\n\n"
                        f"— Mitra"
                    ),
                    reply_context={
                        "type":          "candidate",
                        "session_id":    cand_phone,
                        "intro_id":      intro_id,
                        "scheduling":    True,
                        "founder_slots": slots,
                    },
                )
                log.info(
                    "email-reply: forwarded founder slots to candidate=%s intro=%d slots=%r",
                    cand_email, intro_id, slots,
                )
                # Acknowledge the founder
                await send_email(
                    to=from_email,
                    subject="Re: Candidate Introduction — Mitra",
                    text=(
                        f"Hi {founder},\n\n"
                        f"I've shared your availability with {cand_name} and asked them "
                        f"to confirm a slot. I'll send you both a confirmation as soon as "
                        f"they respond — usually within a few hours.\n\n— Mitra"
                    ),
                    reply_context={"type": "founder", "intro_id": intro_id, "job_id": job_id},
                )
            elif slots and not cand_email:
                # Phone candidate — mark interview and tell founder
                await _update_intro_from_intent(intro_id, intent, reply_text=reply_text[:800])
                await send_email(
                    to=from_email,
                    subject="Re: Candidate Introduction — Mitra",
                    text=(
                        f"Hi {founder},\n\n"
                        f"Got it — I've noted your availability ({slots}) and I'll reach "
                        f"out to {cand_name} directly to confirm a time.\n\n— Mitra"
                    ),
                    reply_context={"type": "founder", "intro_id": intro_id, "job_id": job_id},
                )
            else:
                # No clear slots in the email — ask the founder to share times
                await send_email(
                    to=from_email,
                    subject="Re: Candidate Introduction — Mitra",
                    text=(
                        f"Hi {founder},\n\n"
                        f"Happy to coordinate! Could you share 2–3 specific windows that "
                        f"work for you this week (e.g. Tuesday 2pm, Thursday 11am)? "
                        f"I'll reach out to {cand_name} immediately to confirm.\n\n— Mitra"
                    ),
                    reply_context={"type": "founder", "intro_id": intro_id, "job_id": job_id},
                )
            return  # Scheduling handled — don't send canned response below

        # ── All other intents ─────────────────────────────────────────────────
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
