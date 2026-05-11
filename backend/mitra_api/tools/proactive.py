"""
mitra_api/tools/proactive.py

Proactive workflow engine — makes Mitra act without being prompted.

Seven autonomous behaviours:
  1. candidate_re_engagement       — re-engages candidates who went quiet mid-intake
  2. intro_follow_up               — nudges founders who haven't replied in 48h
  3. acknowledged_no_interview     — nudges founder when interested but no interview booked
  4. stalled_interview_outcome     — asks both sides how interview went after 3 days
  5. pending_offer_check           — checks in with candidate on pending offer after 48h
  6. outcome_check_in              — checks in at 30d / 90d post-placement
  7. founder_pipeline_digest       — pipeline summary to founders on demand

Each function is designed to be called from the scheduler.
None require a human to trigger them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mitra_api.db.models import (
    Candidate, CandidateSignal, Intro, IntroStatus, Job,
)

log = logging.getLogger(__name__)


# ── 1. CANDIDATE RE-ENGAGEMENT ────────────────────────────────────────────────

async def get_stale_candidates(
    db: AsyncSession,
    *,
    idle_hours: int = 48,
    min_signals: int = 2,
    max_signals: int = 6,
) -> list[dict[str, Any]]:
    """
    Find candidates who:
    - Started a conversation (have >= min_signals signals)
    - Have NOT completed intake (< max_signals signals)
    - Haven't been active in idle_hours
    - Have never received an intro

    These are warm leads who fell off mid-conversation.
    Re-engaging them is the highest-ROI proactive action.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=idle_hours)

    candidates = (await db.execute(
        select(Candidate)
        .where(
            Candidate.is_active == True,
            Candidate.updated_at < cutoff,
            not_(Candidate.phone.like("web:%")),
        )
        .order_by(Candidate.updated_at.desc())
    )).scalars().all()

    results = []
    for c in candidates:
        sigs = (await db.execute(
            select(CandidateSignal).where(CandidateSignal.candidate_id == c.id)
        )).scalars().all()
        sig_dict = {s.key: s.value for s in sigs}

        if not (min_signals <= len(sig_dict) < max_signals):
            continue

        # Skip if they already have an intro — they're past the intake stage
        has_intro = (await db.execute(
            select(Intro.id).where(Intro.candidate_id == c.id)
        )).first()
        if has_intro:
            continue

        results.append({
            "candidate_id": c.id,
            "phone":        c.phone,
            "name":         c.name or sig_dict.get("candidate_name", ""),
            "signals":      sig_dict,
            "signal_count": len(sig_dict),
            "idle_since":   c.updated_at.isoformat(),
        })

    return results


def build_re_engagement_message(candidate: dict[str, Any]) -> str:
    """
    Build a personalised re-engagement WhatsApp message.
    References what they actually shared — never generic.
    """
    name  = (candidate.get("name") or "").split()[0] or None
    sigs  = candidate.get("signals", {})

    greeting = f"Hey {name}!" if name else "Hey!"

    stack      = sigs.get("primary_stack")
    role       = sigs.get("current_role")
    company    = sigs.get("current_company")
    motivation = sigs.get("motivation", "")

    if stack and isinstance(stack, list) and stack:
        hook = (
            f"You mentioned {stack[0]} earlier — I've had a couple of new roles "
            f"come in that match that exactly."
        )
    elif role and company:
        hook = (
            f"You mentioned you're at {company} as {role} — I've had a few founders "
            f"ask specifically about candidates with that background."
        )
    elif motivation:
        short_mot = str(motivation)[:80].rstrip()
        hook = (
            f"You mentioned '{short_mot}' — that's exactly what a couple of the "
            f"founders I work with are looking for."
        )
    else:
        hook = "I've had some interesting new roles come in since we last spoke."

    return (
        f"{greeting}\n\n"
        f"{hook}\n\n"
        f"We got partway through our conversation — do you want to pick up where "
        f"we left off? Just reply and I'll have a shortlist ready within minutes.\n\n"
        f"— Mitra"
    )


# ── 2. INTRO FOLLOW-UP ────────────────────────────────────────────────────────

async def get_intros_needing_followup(
    db: AsyncSession,
    *,
    hours_since_sent: int = 48,
) -> list[dict[str, Any]]:
    """
    Find intros that were sent but haven't been acknowledged.
    Returns intros eligible for a follow-up nudge to the founder.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_since_sent)

    rows = (await db.execute(
        select(Intro, Job, Candidate)
        .join(Job,       Intro.job_id       == Job.id)
        .join(Candidate, Intro.candidate_id == Candidate.id)
        .where(
            Intro.status  == IntroStatus.sent,
            Intro.sent_at <= cutoff,
            Intro.sent_at.isnot(None),
        )
        .order_by(Intro.sent_at)
    )).all()

    results = []
    for intro, job, candidate in rows:
        if not (job.founder_wa or job.founder_email):
            continue
        results.append({
            "intro_id":       intro.id,
            "job_id":         job.id,
            "job_title":      job.title,
            "company":        job.company,
            "founder_name":   job.founder_name or "there",
            "founder_wa":     job.founder_wa,
            "founder_email":  job.founder_email,
            "candidate_name": candidate.name or "the candidate",
            "sent_at":        intro.sent_at.isoformat() if intro.sent_at else None,
        })

    return results


def build_founder_followup_message(intro_data: dict[str, Any]) -> str:
    founder   = intro_data.get("founder_name", "there")
    candidate = intro_data.get("candidate_name", "the candidate")
    role      = intro_data.get("job_title", "the role")
    company   = intro_data.get("company", "your company")

    return (
        f"Hi {founder},\n\n"
        f"Quick follow-up on my intro of {candidate} for {role} at {company}.\n\n"
        f"I wanted to make sure this didn't get lost — {candidate} is genuinely "
        f"interested and I'd hate for timing to be the thing that prevents a "
        f"great conversation.\n\n"
        f"Even a quick 'not the right fit right now' helps me understand what to "
        f"send next. Happy to adjust the brief if requirements have changed.\n\n"
        f"— Mitra"
    )


# ── 3. ACKNOWLEDGED → NO INTERVIEW BOOKED ────────────────────────────────────

async def get_acknowledged_no_interview(
    db: AsyncSession,
    *,
    hours_since_acknowledged: int = 120,  # 5 days
) -> list[dict[str, Any]]:
    """
    Find intros where the founder acknowledged interest but no interview
    has been booked after hours_since_acknowledged.
    Nudge: ask the founder if they need help scheduling.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_since_acknowledged)

    rows = (await db.execute(
        select(Intro, Job, Candidate)
        .join(Job,       Intro.job_id       == Job.id)
        .join(Candidate, Intro.candidate_id == Candidate.id)
        .where(
            Intro.status         == IntroStatus.acknowledged,
            Intro.updated_at     <= cutoff,
            Intro.interview_at.is_(None),
        )
        .order_by(Intro.updated_at)
    )).all()

    results = []
    for intro, job, candidate in rows:
        if not (job.founder_wa or job.founder_email):
            continue
        results.append({
            "intro_id":        intro.id,
            "job_title":       job.title,
            "company":         job.company,
            "founder_name":    job.founder_name or "there",
            "founder_wa":      job.founder_wa,
            "founder_email":   job.founder_email,
            "candidate_name":  candidate.name or "the candidate",
            "candidate_phone": candidate.phone,
        })

    return results


def build_acknowledged_nudge_message(intro_data: dict[str, Any]) -> str:
    founder   = intro_data.get("founder_name", "there")
    candidate = intro_data.get("candidate_name", "the candidate")
    role      = intro_data.get("job_title", "the role")

    return (
        f"Hi {founder},\n\n"
        f"Just checking in — you expressed interest in {candidate} for {role}. "
        f"Have you had a chance to connect yet?\n\n"
        f"If you'd like to move forward, I can help coordinate availability. "
        f"Or if your requirements have shifted, just let me know and I'll "
        f"adjust what I send next.\n\n"
        f"— Mitra"
    )


# ── 4. INTERVIEW BOOKED → NO OUTCOME UPDATE ───────────────────────────────────

async def get_stalled_interviews(
    db: AsyncSession,
    *,
    hours_since_interview: int = 72,  # 3 days
) -> list[dict[str, Any]]:
    """
    Find intros with an interview booked but no status update after
    hours_since_interview. Ask both sides how it went.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_since_interview)

    rows = (await db.execute(
        select(Intro, Job, Candidate)
        .join(Job,       Intro.job_id       == Job.id)
        .join(Candidate, Intro.candidate_id == Candidate.id)
        .where(
            Intro.status     == IntroStatus.interview,
            Intro.updated_at <= cutoff,
        )
        .order_by(Intro.updated_at)
    )).all()

    results = []
    for intro, job, candidate in rows:
        results.append({
            "intro_id":        intro.id,
            "job_title":       job.title,
            "company":         job.company,
            "founder_name":    job.founder_name or "there",
            "founder_wa":      job.founder_wa,
            "founder_email":   job.founder_email,
            "candidate_name":  candidate.name or "the candidate",
            "candidate_phone": candidate.phone,
        })

    return results


def build_interview_outcome_candidate(intro_data: dict[str, Any]) -> str:
    name    = (intro_data.get("candidate_name") or "").split()[0] or "hey"
    company = intro_data.get("company", "them")
    role    = intro_data.get("job_title", "the role")

    return (
        f"Hey {name},\n\n"
        f"How did the interview with {company} go for the {role} position?\n\n"
        f"Even a quick 'it went well' or 'not the right fit' helps me know "
        f"where things stand — and whether I should be exploring other options "
        f"for you in parallel.\n\n"
        f"— Mitra"
    )


def build_interview_outcome_founder(intro_data: dict[str, Any]) -> str:
    founder   = intro_data.get("founder_name", "there")
    candidate = intro_data.get("candidate_name", "the candidate")
    role      = intro_data.get("job_title", "the role")

    return (
        f"Hi {founder},\n\n"
        f"How did the interview with {candidate} for {role} go?\n\n"
        f"If you're moving forward, I can help coordinate next steps. "
        f"If not, a quick note on why helps me calibrate what I send next time.\n\n"
        f"— Mitra"
    )


# ── 5. OFFER RECEIVED → NO ACCEPTANCE ────────────────────────────────────────

async def get_pending_offers(
    db: AsyncSession,
    *,
    hours_since_offer: int = 48,
) -> list[dict[str, Any]]:
    """
    Find intros where an offer was extended but the candidate hasn't accepted
    (status still 'offer') after hours_since_offer.
    Nudge: check in with the candidate.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_since_offer)

    rows = (await db.execute(
        select(Intro, Job, Candidate)
        .join(Job,       Intro.job_id       == Job.id)
        .join(Candidate, Intro.candidate_id == Candidate.id)
        .where(
            Intro.status     == IntroStatus.offer,
            Intro.updated_at <= cutoff,
        )
        .order_by(Intro.updated_at)
    )).all()

    results = []
    for intro, job, candidate in rows:
        if candidate.phone.startswith("web:"):
            continue
        results.append({
            "intro_id":        intro.id,
            "job_title":       job.title,
            "company":         job.company,
            "founder_name":    job.founder_name or "there",
            "candidate_name":  candidate.name or "the candidate",
            "candidate_phone": candidate.phone,
        })

    return results


def build_offer_pending_message(intro_data: dict[str, Any]) -> str:
    name    = (intro_data.get("candidate_name") or "").split()[0] or "hey"
    company = intro_data.get("company", "them")
    role    = intro_data.get("job_title", "the role")

    return (
        f"Hey {name},\n\n"
        f"Congratulations on the offer from {company} for {role}!\n\n"
        f"Are you leaning towards accepting? If you're weighing it up or have "
        f"questions about the comp, equity, or role scope — I'm happy to help "
        f"you think it through.\n\n"
        f"And if you decide not to take it, just let me know — I'll keep your "
        f"search active.\n\n"
        f"— Mitra"
    )


# ── 6. POST-PLACEMENT OUTCOME CHECK-IN ───────────────────────────────────────

async def get_placements_for_checkin(
    db: AsyncSession,
    *,
    days: int = 30,
    window_days: int = 7,
) -> list[dict[str, Any]]:
    """
    Find placements that hit the `days` milestone this week.
    Returns both candidate and founder contacts for dual check-in.
    """
    now      = datetime.now(timezone.utc)
    target   = now - timedelta(days=days)
    earliest = target - timedelta(days=window_days)

    rows = (await db.execute(
        select(Intro, Job, Candidate)
        .join(Job,       Intro.job_id       == Job.id)
        .join(Candidate, Intro.candidate_id == Candidate.id)
        .where(
            Intro.status   == IntroStatus.hired,
            Intro.hired_at >= earliest,
            Intro.hired_at <= target,
        )
    )).all()

    results = []
    for intro, job, candidate in rows:
        results.append({
            "intro_id":        intro.id,
            "days":            days,
            "candidate_name":  candidate.name or "there",
            "candidate_phone": candidate.phone,
            "company":         job.company,
            "role":            job.title,
            "founder_name":    job.founder_name,
            "founder_wa":      job.founder_wa,
            "founder_email":   job.founder_email,
        })

    return results


def build_candidate_checkin_message(placement: dict[str, Any]) -> str:
    days    = placement.get("days", 30)
    name    = (placement.get("candidate_name") or "").split()[0] or "hey"
    company = placement.get("company", "your new company")
    role    = placement.get("role", "the role")

    if days == 30:
        timeframe = "first month"
        ask = "What's been the biggest surprise — good or bad?"
    else:
        timeframe = "first 90 days"
        ask = (
            "Is the role what was described? And is there anything I should know "
            "for future candidates I send their way?"
        )

    return (
        f"Hey {name},\n\n"
        f"It's been {days} days since you joined {company} as {role} — "
        f"hope the {timeframe} has gone well.\n\n"
        f"{ask}\n\n"
        f"Genuinely asking — your honest take helps me give better advice to "
        f"engineers making a similar move.\n\n"
        f"— Mitra"
    )


def build_founder_checkin_message(placement: dict[str, Any]) -> str:
    days      = placement.get("days", 30)
    founder   = placement.get("founder_name") or "there"
    candidate = placement.get("candidate_name", "the candidate")
    role      = placement.get("role", "the role")

    return (
        f"Hi {founder},\n\n"
        f"Quick check-in — it's been {days} days since {candidate} joined as {role}.\n\n"
        f"How are they settling in? Is the role what you expected?\n\n"
        f"Your honest feedback — even just a line — helps me send better candidates "
        f"next time and understand what actually predicts a successful placement.\n\n"
        f"— Mitra"
    )


# ── 4. FOUNDER PIPELINE DIGEST ───────────────────────────────────────────────

async def get_founder_pipeline_state(
    job_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    rows = (await db.execute(
        select(Intro, Candidate)
        .join(Candidate, Intro.candidate_id == Candidate.id)
        .where(Intro.job_id == job_id)
        .order_by(Intro.sent_at.desc())
    )).all()

    by_status: dict[str, list[str]] = {}
    for intro, candidate in rows:
        status = str(intro.status.value if hasattr(intro.status, "value") else intro.status)
        name   = candidate.name or "Candidate"
        by_status.setdefault(status, []).append(name)

    return {"job_id": job_id, "total": len(rows), "by_status": by_status}


def build_founder_digest_message(
    founder_name: str,
    job_title: str,
    company: str,
    pipeline: dict[str, Any],
) -> str:
    by_status = pipeline.get("by_status", {})
    total     = pipeline.get("total", 0)

    if total == 0:
        return (
            f"Hi {founder_name},\n\n"
            f"Quick update on the {job_title} search at {company} — "
            f"I'm actively matching candidates but haven't found a strong enough fit "
            f"to introduce yet. I'll be in touch as soon as I do.\n\n"
            f"— Mitra"
        )

    status_labels = {
        "sent":         "Intro sent, waiting for reply",
        "acknowledged": "Replied — conversation in progress",
        "interview":    "Interview booked",
        "offer":        "Offer made",
        "hired":        "Hired",
        "declined":     "Passed",
        "ghosted":      "No reply (I'll follow up)",
    }

    lines = [f"Hi {founder_name},\n\nQuick update on the {job_title} pipeline at {company}:\n"]
    for status, names in by_status.items():
        label     = status_labels.get(status, status.title())
        names_str = ", ".join(names[:3])
        if len(names) > 3:
            names_str += f" (+{len(names) - 3} more)"
        lines.append(f"• {label}: {names_str}")

    lines.append(
        f"\n{total} total introduction{'s' if total != 1 else ''} sent so far.\n\n"
        f"Anything I should adjust in the brief? Happy to tighten the search.\n\n"
        f"— Mitra"
    )
    return "\n".join(lines)


# ── DELIVERY HELPER ───────────────────────────────────────────────────────────

async def send_proactive_message(
    phone: str,
    message: str,
    *,
    label: str = "proactive",
) -> bool:
    """
    Send a proactive WhatsApp message to any phone number.
    Returns True on success.
    """
    digits = "".join(c for c in phone if c.isdigit())
    wa_to  = f"whatsapp:+{digits}"

    try:
        from mitra_api.twilio_whatsapp.client import send_whatsapp_reply
        await send_whatsapp_reply(to_whatsapp_from_value=wa_to, body=message)
        log.info("proactive [%s] sent to %s", label, phone)
        return True
    except Exception:
        log.exception("proactive [%s] failed for %s", label, phone)
        return False
