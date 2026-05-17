"""
mitra_api/tools/notifications.py

Proactive job alert notifications — the engine that makes Mitra feel like
a real talent agent instead of a passive chatbot.

When a new job is added (or its content changes), this module:
  1. Loads all active candidates with enough signals to match against
  2. Gates on fast signal matching (stack overlap, salary, dealbreakers)
  3. Scores qualifiers with dimensional fit scoring (salary/location/skill)
  4. Ranks by overall_fit and sends the top matches — quality over quantity

No LLM calls — pure signal + fit scoring keeps this fast and cheap at scale.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mitra_api.db.models import Candidate, CandidateSignal, Intro, Job, JobStatus

log = logging.getLogger(__name__)

# Send top N by fit score — quality gate replaces a blunt count cap
_MAX_ALERTS_PER_JOB = 30
_MIN_OVERALL_FIT = 0.45  # don't send alerts below this overall fit score


# ── Signal-based match scoring ────────────────────────────────────────────────

def _normalize_list(value: Any) -> list[str]:
    """Coerce JSONB value to a flat list of lowercase strings."""
    if isinstance(value, list):
        return [str(v).strip().lower() for v in value if v]
    if isinstance(value, str) and value.strip():
        return [s.strip().lower() for s in value.split(",") if s.strip()]
    return []


def _score_candidate_for_job(
    signals: dict[str, Any],
    job: Job,
) -> tuple[bool, str]:
    """
    Returns (is_match, why_line).

    Match criteria (all must pass):
      1. Candidate has primary_stack signal (no stack = incomplete profile, skip)
      2. If job has a defined stack, candidate must overlap on ≥1 tech
      3. Candidate salary expectation ≤ job max salary × 1.2 (20% negotiation buffer)
      4. Candidate dealbreakers don't match the job's sector or company name
    """
    # ── 1. Must have a stack ─────────────────────────────────────────────────
    raw_stack = signals.get("primary_stack") or signals.get("tech_stack") or signals.get("stack")
    candidate_stack_raw: list[str] = (
        raw_stack if isinstance(raw_stack, list) else
        [s.strip() for s in str(raw_stack).split(",") if s.strip()] if raw_stack else []
    )
    if not candidate_stack_raw:
        return False, ""

    candidate_stack_lower = {s.lower().strip() for s in candidate_stack_raw if s}

    # ── 2. Stack overlap ─────────────────────────────────────────────────────
    job_stack_lower: set[str] = set()
    if job.stack:
        job_stack_lower = {s.lower().strip() for s in (
            job.stack if isinstance(job.stack, list) else [job.stack]
        ) if s}

    overlap = candidate_stack_lower & job_stack_lower
    if job_stack_lower and not overlap:
        return False, ""

    # ── 3. Salary fit ────────────────────────────────────────────────────────
    salary_target = signals.get("salary_target_lpa") or signals.get("salary_floor_lpa")
    if salary_target and job.salary_max_lpa:
        try:
            if float(salary_target) > float(job.salary_max_lpa) * 1.2:
                return False, ""
        except (TypeError, ValueError):
            pass

    # ── 4. Dealbreaker check ─────────────────────────────────────────────────
    dealbreakers = _normalize_list(signals.get("dealbreakers"))
    job_sector  = (job.sector  or "").lower()
    job_company = (job.company or "").lower()
    for word in dealbreakers:
        if word and (word in job_sector or word in job_company):
            return False, ""

    # ── Build why_line ───────────────────────────────────────────────────────
    if overlap:
        # Use original casing from candidate stack
        matched = next(
            (t for t in candidate_stack_raw if t.lower() in job_stack_lower),
            next(iter(overlap)),
        )
        why_line = f"your {matched} background is exactly what they need"
    elif job.stage:
        why_line = f"matches your preference for {job.stage} startups"
    else:
        why_line = "strong overall fit based on your profile"

    return True, why_line


# ── Alert message builder ─────────────────────────────────────────────────────

def _build_fit_why_line(
    signals: dict[str, Any],
    job: Job,
    fit_scores: dict[str, float],
    signal_why: str,
) -> str:
    """
    Build a personalised why-line from dimensional fit scores.
    Picks the strongest dimension to lead with for specificity.
    """
    salary_fit   = fit_scores.get("salary_fit", 0.5)
    location_fit = fit_scores.get("location_fit", 0.5)
    skill_fit    = fit_scores.get("skill_fit", 0.5)

    # Lead with the strongest dimension
    if skill_fit >= 0.75 and signal_why:
        return signal_why  # specific tech match beats generic
    if salary_fit >= 0.85:
        sal = signals.get("salary_target_lpa") or signals.get("salary_floor_lpa")
        if sal and job.salary_max_lpa:
            return f"the ₹{job.salary_max_lpa}L ceiling fits your expectations well"
    if location_fit >= 0.85:
        pref = signals.get("location_preference")
        if pref:
            loc = pref[0] if isinstance(pref, list) else str(pref)
            return f"the {loc} setup matches what you told me you need"
    if signal_why:
        return signal_why
    stage_pref = signals.get("startup_stage_pref")
    if stage_pref and job.stage:
        stages = stage_pref if isinstance(stage_pref, list) else [stage_pref]
        if any(job.stage.lower() in s.lower() for s in stages):
            return f"matches your preference for {job.stage} companies"
    return "strong overall fit based on your full profile"


def _build_alert_message(
    *,
    name: str,
    job: Job,
    why_line: str,
    fit_scores: dict[str, float] | None = None,
) -> str:
    greeting = f"Hey {name.split()[0]}!" if name else "Hey!"

    # Location / remote line
    loc_parts: list[str] = []
    if job.stage:
        loc_parts.append(job.stage)
    if job.remote_policy:
        loc_parts.append(job.remote_policy.capitalize())
    if job.location and job.location.lower() != (job.remote_policy or "").lower():
        loc_parts.append(job.location)
    meta_line = " · ".join(loc_parts) if loc_parts else ""

    # Salary line
    salary_line = ""
    if job.salary_min_lpa and job.salary_max_lpa:
        salary_line = f"\nSalary: ₹{job.salary_min_lpa}–{job.salary_max_lpa}L"
    elif job.salary_max_lpa:
        salary_line = f"\nSalary: up to ₹{job.salary_max_lpa}L"

    # Stack tags (top 4)
    stack_tags = ""
    if job.stack and isinstance(job.stack, list):
        tags = [str(s) for s in job.stack[:4] if s]
        if tags:
            stack_tags = f"\nStack: {', '.join(tags)}"

    # Fit confidence line — only show if notably strong
    fit_note = ""
    if fit_scores and fit_scores.get("overall_fit", 0) >= 0.75:
        fit_note = "\n✓ Strong match across salary, location, and stack."

    body = (
        f"{greeting}\n\n"
        f"New role just in — I think this one fits you:\n\n"
        f"*{job.title}* at *{job.company}*\n"
    )
    if meta_line:
        body += f"{meta_line}\n"
    body += salary_line
    body += stack_tags
    body += fit_note
    body += (
        f"\n\n{why_line.capitalize()}.\n\n"
        f"Interested? Just reply and I'll make the intro.\n\n"
        f"— Mitra"
    )
    return body.strip()


# ── Core notification function ─────────────────────────────────────────────────

async def notify_matching_candidates(job_id: int, db: AsyncSession) -> int:
    """
    Find candidates that match the given job and send them a WhatsApp alert.
    Returns the number of alerts sent.

    Called as a background task after job creation or content update.
    """
    # Load job
    job = (await db.execute(
        select(Job).where(Job.id == job_id, Job.status == JobStatus.active)
    )).scalar_one_or_none()

    if not job:
        log.warning("notify_matching_candidates: job %d not found or not active", job_id)
        return 0

    # Load candidates who already have an intro to this job (skip them)
    already_intro_ids: set[int] = set(
        row[0] for row in (await db.execute(
            select(Intro.candidate_id).where(Intro.job_id == job_id)
        )).all()
    )

    # Load all active candidates — ordered by most recently updated (most engaged first)
    candidates = (await db.execute(
        select(Candidate)
        .where(Candidate.is_active == True)
        .order_by(Candidate.updated_at.desc())
    )).scalars().all()

    from mitra_api.tools.fit_score import compute_fit_scores

    # ── Phase 1: Signal gate + fit scoring ───────────────────────────────────
    # Score all candidates, collect qualified matches ranked by overall_fit.
    qualified: list[dict[str, Any]] = []

    for candidate in candidates:
        if candidate.id in already_intro_ids:
            continue
        if not candidate.phone or candidate.phone.startswith("web:"):
            continue

        sig_rows = (await db.execute(
            select(CandidateSignal).where(CandidateSignal.candidate_id == candidate.id)
        )).scalars().all()
        signals: dict[str, Any] = {row.key: row.value for row in sig_rows}

        if candidate.name:
            signals.setdefault("candidate_name", candidate.name)
        if candidate.current_role:
            signals.setdefault("current_role", candidate.current_role)

        # Fast signal gate — eliminates obvious mismatches cheaply
        is_match, signal_why = _score_candidate_for_job(signals, job)
        if not is_match:
            continue

        # Dimensional fit scoring for ranking and message personalisation
        fit_scores = compute_fit_scores(
            signals=signals,
            job_salary_min=job.salary_min_lpa,
            job_salary_max=job.salary_max_lpa,
            job_location=job.location,
            job_remote_policy=job.remote_policy,
            job_stack=job.stack if isinstance(job.stack, list) else None,
        )

        if fit_scores["overall_fit"] < _MIN_OVERALL_FIT:
            log.debug(
                "notify: skipping candidate=%s overall_fit=%.2f < threshold",
                candidate.phone, fit_scores["overall_fit"],
            )
            continue

        why_line = _build_fit_why_line(signals, job, fit_scores, signal_why)

        qualified.append({
            "candidate": candidate,
            "signals":   signals,
            "fit_scores": fit_scores,
            "why_line":  why_line,
        })

    # ── Phase 2: Rank by overall_fit, take top N ─────────────────────────────
    qualified.sort(key=lambda x: x["fit_scores"]["overall_fit"], reverse=True)
    to_send = qualified[:_MAX_ALERTS_PER_JOB]

    log.info(
        "notify_matching_candidates: job=%d qualified=%d sending=%d",
        job_id, len(qualified), len(to_send),
    )

    # ── Phase 3: Send alerts ──────────────────────────────────────────────────
    sent = 0
    for item in to_send:
        candidate  = item["candidate"]
        fit_scores = item["fit_scores"]
        why_line   = item["why_line"]
        name       = candidate.name or item["signals"].get("candidate_name") or ""
        message    = _build_alert_message(
            name=name, job=job, why_line=why_line, fit_scores=fit_scores,
        )

        digits = "".join(c for c in candidate.phone if c.isdigit())
        wa_to  = f"whatsapp:+{digits}"

        try:
            from mitra_api.twilio_whatsapp.client import send_whatsapp_reply
            await send_whatsapp_reply(to_whatsapp_from_value=wa_to, body=message)
            sent += 1
            log.info(
                "job alert sent: job=%d (%s @ %s) → candidate=%s fit=%.2f",
                job_id, job.title, job.company,
                candidate.phone, fit_scores["overall_fit"],
            )
        except Exception:
            log.exception(
                "job alert failed: job=%d → candidate=%s", job_id, candidate.phone
            )

    log.info(
        "notify_matching_candidates complete: job=%d sent=%d / %d qualified",
        job_id, sent, len(qualified),
    )
    return sent


# ── Background-safe wrapper ───────────────────────────────────────────────────

async def notify_matching_candidates_bg(job_id: int) -> None:
    """
    Self-contained background task wrapper — opens its own DB session so it
    can run safely after the originating request session has closed.
    """
    from mitra_api.db.engine import get_session_factory
    factory = get_session_factory()
    try:
        async with factory() as db:
            count = await notify_matching_candidates(job_id, db)
            log.info("background alert task done: job=%d alerts_sent=%d", job_id, count)
    except Exception:
        log.exception("background alert task failed for job=%d", job_id)
