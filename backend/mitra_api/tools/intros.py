"""
mitra_api/tools/intros.py

Records every introduction Mitra makes and sends the warm intro to the founder.

Delivery:
  - founder_wa    → Twilio WhatsApp
  - founder_email → Resend email (plain text)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mitra_api.db.models import Candidate, CandidateSignal, Intro, IntroStatus, Job
from mitra_api.tools.candidates import upsert_candidate

log = logging.getLogger(__name__)

# Signals that make an intro strong — checked for thin-intro detection, not as a gate
_QUALITY_SIGNALS = ("candidate_name", "primary_stack", "current_role")


# ── Intro message builder ─────────────────────────────────────────────────────

def _build_intro(
    *,
    candidate: Candidate,
    job: Job,
    signals: dict[str, Any],
    why_note: str,
) -> str:
    """Compose a strong, signal-rich warm intro message."""

    name = candidate.name or signals.get("candidate_name") or "the candidate"

    # Stack
    raw_stack = signals.get("primary_stack", [])
    stack_str = (
        ", ".join(str(s) for s in raw_stack[:6]) if isinstance(raw_stack, list)
        else str(raw_stack)
    ).strip() or "not yet specified"

    # Experience
    years = candidate.years_exp or signals.get("years_experience")
    years_str = f"{years} years" if years else "several years"

    # Current position
    role    = candidate.current_role    or signals.get("current_role",    "Engineer")
    company = candidate.current_company or signals.get("current_company", "their current company")

    # Motivation
    motivation = signals.get("motivation") or signals.get("what_they_want") or ""
    if isinstance(motivation, list):
        motivation = "; ".join(str(m) for m in motivation)
    motivation = str(motivation).strip() or "building high-ownership products at startup scale"

    # Salary
    salary_target = signals.get("salary_target_lpa") or signals.get("salary_floor_lpa")
    salary_line = f"• Salary expectation: ₹{salary_target} LPA\n" if salary_target else ""

    # Notice period
    notice = signals.get("notice_period_days") or signals.get("notice_period")
    notice_line = f"• Notice period: {notice} days\n" if notice else ""

    # Stage preference
    stage_pref = signals.get("startup_stage_pref") or signals.get("stage_preference")
    if isinstance(stage_pref, list):
        stage_pref = ", ".join(str(s) for s in stage_pref)
    stage_line = f"• Stage preference: {stage_pref}\n" if stage_pref else ""

    # Notable projects / what they've built
    built = signals.get("notable_projects") or signals.get("proud_of") or signals.get("built")
    built_line = f"• Built: {built}\n" if built else ""

    # Dealbreakers — skip in intro (not relevant to founder)
    # Extra signals to surface
    extra_lines = ""
    for key in ("sector_preference", "open_to_relocate", "actively_looking"):
        val = signals.get(key)
        if val is not None and str(val).strip():
            label = key.replace("_", " ").title()
            extra_lines += f"• {label}: {val}\n"

    profile_block = (
        f"• {years_str} of experience — currently *{role}* at {company}\n"
        f"• Stack: {stack_str}\n"
        f"{built_line}"
        f"{salary_line}"
        f"{notice_line}"
        f"{stage_line}"
        f"{extra_lines}"
        f"• What they want next: {motivation}"
    ).rstrip()

    founder_name = job.founder_name or "there"

    return (
        f"Hi {founder_name},\n\n"
        f"I'm Mitra — a talent agent that places engineers directly with funded startups in India. "
        f"I only make an introduction when I'm confident about the fit.\n\n"
        f"I'd like to introduce you to *{name}*, for your *{job.title}* role at {job.company}.\n\n"
        f"*Why I'm making this intro:*\n"
        f"{why_note.strip()}\n\n"
        f"*{name}'s profile:*\n"
        f"{profile_block}\n\n"
        f"I've spent time understanding both {name}'s goals and what you're building at {job.company}. "
        f"This isn't a spray-and-pray intro — I'd put my reputation on this one.\n\n"
        f"Would you have 20 minutes this week to connect? Happy to share their CV or jump on a call.\n\n"
        f"— Mitra"
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_twilio_wa(number: str) -> str:
    s = number.strip()
    if s.lower().startswith("whatsapp:"):
        s = s[9:].strip()
    digits = "".join(c for c in s if c.isdigit())
    return f"whatsapp:+{digits}"


async def _load_candidate_signals(candidate_id: int, session: AsyncSession) -> dict[str, Any]:
    result = await session.execute(
        select(CandidateSignal).where(CandidateSignal.candidate_id == candidate_id)
    )
    return {row.key: row.value for row in result.scalars().all()}


async def _send_intro(*, founder_wa: str | None, founder_email: str | None,
                      subject: str, body: str) -> bool:
    """
    Deliver intro to founder.  Returns True if at least one channel succeeded.
    Also BCC's ops email (MITRA_OPS_EMAIL) so every intro is visible to the team.
    """
    from mitra_api.config import get_settings
    from mitra_api.tools.email import send_email

    s = get_settings()
    ops_email = s.mitra_ops_email.strip()
    sent = False

    if founder_wa:
        try:
            from mitra_api.twilio_whatsapp.client import send_whatsapp_reply
            await send_whatsapp_reply(to_whatsapp_from_value=_to_twilio_wa(founder_wa), body=body)
            log.info("intro sent via WhatsApp to %s", founder_wa)
            sent = True
        except Exception:
            log.exception("WhatsApp intro send failed for %s", founder_wa)

    if founder_email and not sent:
        try:
            sent = await send_email(to=founder_email, subject=subject, text=body)
        except Exception:
            log.exception("email intro send failed for %s", founder_email)

    # BCC ops on every successful founder delivery
    if sent and ops_email and ops_email not in (founder_email or ""):
        try:
            await send_email(to=ops_email, subject=f"[BCC] {subject}", text=body)
        except Exception:
            log.warning("ops BCC email failed (non-critical)")

    # Fallback: no founder channel — route to ops inbox so intro is not lost
    if not sent and ops_email:
        no_channel_note = (
            f"[NO FOUNDER CHANNEL — ops fallback]\n"
            f"founder_email={founder_email!r}  founder_wa={founder_wa!r}\n\n"
            + body
        )
        try:
            sent = await send_email(to=ops_email, subject=f"[NEEDS RELAY] {subject}", text=no_channel_note)
            if sent:
                log.info("intro routed to ops fallback (%s) — no founder channel", ops_email)
        except Exception:
            log.exception("ops fallback email failed for %s", ops_email)

    return sent


# ── Public API ────────────────────────────────────────────────────────────────

async def request_intro(
    *,
    candidate_phone: str,
    job_external_id: str,
    why_note: str,
    session: AsyncSession,
) -> dict[str, Any]:
    """
    Create an intro record and send the warm intro to the founder.

    Returns:
        ok                – bool
        needs_more_info   – bool (if minimum profile signals are missing)
        missing_signals   – list[str] (which signals to collect first)
        intro_id          – int
        message           – confirmation/error text for the candidate
        founder_contacted – bool
    """
    # ── Upsert candidate ──────────────────────────────────────────────────────
    candidate = await upsert_candidate(candidate_phone, session=session)

    # ── Load signals early so we can gate on completeness ────────────────────
    signals = await _load_candidate_signals(candidate.id, session)

    # Mirror top-level candidate fields into signals for the check
    if candidate.name and "candidate_name" not in signals:
        signals["candidate_name"] = candidate.name
    if candidate.current_role and "current_role" not in signals:
        signals["current_role"] = candidate.current_role

    missing = [k for k in _QUALITY_SIGNALS if not signals.get(k)]
    if missing:
        log.info(
            "request_intro: sending with thin profile — missing signals %s for %s",
            missing, candidate_phone,
        )

    # ── Look up job ───────────────────────────────────────────────────────────
    job = (await session.execute(
        select(Job).where(Job.external_id == job_external_id, Job.status == "active")
    )).scalar_one_or_none()

    if not job:
        try:
            numeric_id = int(job_external_id)
            job = (await session.execute(
                select(Job).where(Job.id == numeric_id, Job.status == "active")
            )).scalar_one_or_none()
        except (ValueError, TypeError):
            pass

    if not job:
        log.warning("request_intro: job not found — job_external_id=%r", job_external_id)
        return {"ok": False, "message": f"I couldn't find an active role with id '{job_external_id}'. Please share the job title or company name and I'll look it up."}

    # ── Duplicate check — allow strengthen if original was thin ──────────────
    existing_intro = (await session.execute(
        select(Intro).where(Intro.candidate_id == candidate.id, Intro.job_id == job.id)
    )).scalar_one_or_none()

    if existing_intro:
        old_note = existing_intro.intro_note or ""
        signals_now_complete = all(signals.get(k) for k in _QUALITY_SIGNALS)
        intro_was_thin = any(
            marker in old_note
            for marker in ("not specified", "several years", "their current company", "+91")
        )

        if signals_now_complete and intro_was_thin:
            # We can now send a richer follow-up to the founder
            log.info(
                "request_intro: existing intro was thin — sending enriched follow-up "
                "for candidate=%s job=%s", candidate_phone, job_external_id
            )
            enriched_note = _build_intro(
                candidate=candidate, job=job, signals=signals, why_note=why_note
                    or "Wanted to share a fuller picture of this candidate's background.",
            )
            followup_note = (
                f"Hi {job.founder_name or 'there'},\n\n"
                f"Quick follow-up on my earlier intro of {candidate.name or 'the candidate'} "
                f"for the *{job.title}* role. I now have their complete profile and wanted to "
                f"share it properly:\n\n"
                + "\n".join(enriched_note.split("\n")[4:])  # skip the opening preamble, keep profile
            )
            existing_intro.intro_note = enriched_note
            existing_intro.sent_at    = datetime.now(timezone.utc)
            await session.flush()
            subject = f"Follow-up: {candidate.name or 'Candidate'} → {job.title} at {job.company} (full profile)"
            await _send_intro(
                founder_wa=job.founder_wa, founder_email=job.founder_email,
                subject=subject, body=followup_note,
            )
            await session.commit()
            return {
                "ok": True,
                "intro_id": existing_intro.id,
                "strengthened": True,
                "message": (
                    f"I've sent an updated intro to {job.founder_name or 'the founder'} at {job.company} "
                    f"with your complete profile. This one is much stronger — they now have your full "
                    f"background, stack, and what you're looking for."
                ),
                "founder_contacted": True,
            }

        # Original was already complete or signals still missing — don't resend
        return {
            "ok": False,
            "message": (
                f"Your intro to {job.company} was already sent. "
                + ("I'll let you know as soon as they respond." if not intro_was_thin
                   else "Share your name, stack, and current role so I can send a stronger version.")
            ),
        }

    # ── Build intro message ───────────────────────────────────────────────────
    intro_note = _build_intro(
        candidate=candidate,
        job=job,
        signals=signals,
        why_note=why_note or "Strong technical and cultural fit based on their full profile.",
    )

    # ── Persist intro record ──────────────────────────────────────────────────
    intro = Intro(
        candidate_id=candidate.id,
        job_id=job.id,
        status=IntroStatus.sent,
        intro_note=intro_note,
        sent_at=datetime.now(timezone.utc),
    )
    session.add(intro)
    await session.flush()

    # ── Deliver to founder (+ ops BCC / fallback) ────────────────────────────
    subject = f"Intro: {candidate.name or 'A candidate'} → {job.title} at {job.company}"
    founder_contacted = await _send_intro(
        founder_wa=job.founder_wa,
        founder_email=job.founder_email,
        subject=subject,
        body=intro_note,
    )

    if not founder_contacted:
        log.warning(
            "intro id=%d: delivery failed (founder_wa=%s founder_email=%s) — "
            "ops fallback also failed; intro is persisted in DB only",
            intro.id, job.founder_wa, job.founder_email,
        )

    await session.commit()
    log.info(
        "intro id=%d candidate=%s job=%s company=%s founder_contacted=%s",
        intro.id, candidate_phone, job_external_id, job.company, founder_contacted,
    )

    # ── Candidate confirmation email ──────────────────────────────────────────
    # Derive candidate email: web sessions use "web:{email}" as the phone field.
    candidate_email = candidate_phone.removeprefix("web:").strip()
    if "@" in candidate_email:
        try:
            from mitra_api.tools.email import send_email
            candidate_name = candidate.name or "there"
            confirmation_body = (
                f"Hi {candidate_name},\n\n"
                f"Your intro to {job.founder_name or 'the founder'} at {job.company} "
                f"for the {job.title} role has been submitted.\n\n"
                f"Here's what was sent on your behalf:\n\n"
                f"{'—' * 40}\n"
                f"{intro_note}\n"
                f"{'—' * 40}\n\n"
                f"You'll hear from us as soon as there's a response. "
                f"Typical turnaround is 24–48 hours.\n\n"
                f"— Mitra"
            )
            await send_email(
                to=candidate_email,
                subject=f"Your intro to {job.company} has been sent · Mitra",
                text=confirmation_body,
            )
        except Exception:
            log.warning("candidate confirmation email failed for %s (non-critical)", candidate_email)

    return {
        "ok": True,
        "intro_id": intro.id,
        "message": (
            f"Done — I've sent your intro to {job.founder_name or 'the founder'} at {job.company}. "
            f"They typically respond within 24–48 hours. "
            f"Check your inbox — I've sent you a copy of what was shared."
        ),
        "founder_contacted": founder_contacted,
    }


async def get_intro_status(
    *,
    candidate_phone: str,
    job_external_id: str,
    session: AsyncSession,
) -> dict[str, Any]:
    candidate = (await session.execute(
        select(Candidate).where(Candidate.phone == candidate_phone)
    )).scalar_one_or_none()
    if not candidate:
        return {"found": False}

    row = (await session.execute(
        select(Intro, Job)
        .join(Job, Intro.job_id == Job.id)
        .where(Intro.candidate_id == candidate.id, Job.external_id == job_external_id)
    )).first()
    if not row:
        return {"found": False}

    intro, job = row
    status_messages = {
        IntroStatus.sent:         f"Your intro to {job.company} was sent. Waiting to hear back.",
        IntroStatus.acknowledged: f"The founder at {job.company} has seen your intro.",
        IntroStatus.interview:    f"Interview booked with {job.company}.",
        IntroStatus.offer:        f"You have an offer from {job.company}.",
        IntroStatus.hired:        f"Congratulations — you joined {job.company}!",
        IntroStatus.declined:     f"The {job.company} role didn't move forward this time.",
        IntroStatus.ghosted:      f"No reply from {job.company} yet — I'll follow up.",
    }
    return {
        "found": True,
        "status": intro.status,
        "company": job.company,
        "role": job.title,
        "message": status_messages.get(intro.status, f"Status: {intro.status}"),
        "sent_at": intro.sent_at.isoformat() if intro.sent_at else None,
    }
