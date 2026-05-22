"""
mitra_api/tools/intros.py

Records every introduction Mitra makes and sends the warm intro to the founder.

Delivery:
  - founder_wa    → Twilio WhatsApp
  - founder_email → Resend email (plain text)
"""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mitra_api.db.models import Candidate, CandidateSignal, Intro, IntroStatus, Job, Match
from mitra_api.tools.candidates import upsert_candidate
from mitra_api.tools.compatibility import compute_compatibility
from mitra_api.tools.fit_score import compute_fit_scores

log = logging.getLogger(__name__)


def _founder_contact(job: Job) -> tuple[str | None, str | None, str | None]:
    """
    Return (founder_name, founder_email, founder_wa) for a job.
    Checks job-level fields first; falls back to the linked Company row.
    This handles ATS-synced jobs where contact lives only on the Company.
    """
    name  = job.founder_name  or (job.company_rel.founder_name  if job.company_rel else None)
    email = job.founder_email or (job.company_rel.founder_email if job.company_rel else None)
    wa    = job.founder_wa    or (job.company_rel.founder_wa    if job.company_rel else None)
    return name, email, wa


def normalize_why_note_for_founder(text: str, candidate_name: str | None) -> str:
    """
    Ensure intro "why" blurbs read as the founder being addressed *about* the candidate.

    Model output sometimes uses second person ("your background… you would…") as if speaking
    to the candidate; founders and the portal expect third person (name / they / their).
    """
    if not text or not str(text).strip():
        return text
    t = str(text)
    poss = (
        f"{candidate_name.strip()}'s"
        if candidate_name and str(candidate_name).strip()
        else "Their"
    )
    si = r"(^|[.!?][\"']?\s+)"
    t = re.sub(si + r"Your\b", lambda m: m.group(1) + poss, t)
    for label, repl in (
        (r"You're\b", "They're"),
        (r"You've\b", "They've"),
        (r"You'd\b", "They'd"),
        (r"You'll\b", "They'll"),
        (r"You would\b", "They would"),
        (r"You will\b", "They will"),
        (r"You are\b", "They are"),
        (r"You\b", "They"),
    ):
        t = re.sub(si + label, lambda m, r=repl: m.group(1) + r, t)
    mid = (
        (r"\bmakes you an\b", "makes them an"),
        (r"\bmakes you a\b", "makes them a"),
        (r"\byou would\b", "they would"),
        (r"\byou'll\b", "they'll"),
        (r"\byou've\b", "they've"),
        (r"\byou'd\b", "they'd"),
        (r"\byou're an\b", "they're an"),
        (r"\byou're a\b", "they're a"),
        (r"\byou're\b", "they're"),
        (r"\byou will\b", "they will"),
        (r"\byou are\b", "they are"),
        (r"\byour (background|experience|expertise|skills|strengths?|track record|work)\b", r"their \1"),
    )
    for pat, rep in mid:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    return t

# ── Intro gate ─────────────────────────────────────────────────────────────────

# Hard-required: without these the intro message is hollow
_GATE_REQUIRED = {
    "candidate_name": "your full name",
    "primary_stack":  "your primary tech stack (e.g. Python, React)",
    "current_role":   "your current job title",
}
# At least one salary signal must be present (cover interpreter + tool inline args)
_SALARY_SIGNALS = (
    "salary_floor_lpa",
    "salary_target_lpa",
    "salary_min_lpa",
    "salary_max_lpa",
    "current_ctc_lpa",
)

# Soft-required: collected if missing but don't block the intro
_SOFT_SIGNALS = ("notice_period_days", "motivation")


def _gate_missing(signals: dict) -> list[str]:
    """Return human-readable labels for every hard-required field that is absent."""
    missing: list[str] = []
    for key, label in _GATE_REQUIRED.items():
        if not signals.get(key):
            missing.append(label)
    if not any(signals.get(k) for k in _SALARY_SIGNALS):
        missing.append("your salary expectation (floor or target in LPA)")
    return missing


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

    founder_name, _, _ = _founder_contact(job)
    founder_name = founder_name or "there"

    return (
        f"Hi {founder_name},\n\n"
        f"I'm Mitra — a talent agent that places engineers directly with funded startups in India. "
        f"I only make an introduction when I'm confident about the fit.\n\n"
        f"I'd like to introduce you to *{name}*, for your *{job.title}* role at {job.company}.\n\n"
        f"*Why I'm making this intro:*\n"
        f"{normalize_why_note_for_founder(why_note.strip(), name)}\n\n"
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


def _build_response_links(
    token: str,
    candidate_name: str,
    job_title: str,
    company: str,
    founder_access_token: str | None = None,
) -> str:
    """Build the one-click founder reply footer appended to every intro email."""
    from mitra_api.config import get_settings
    s = get_settings()
    api_base  = s.mitra_api_base_url.rstrip("/")
    web_base  = getattr(s, "mitra_web_base_url", "").rstrip("/") or api_base

    interested_url = f"{api_base}/founder/respond?token={token}&action=interested"
    not_fit_url    = f"{api_base}/founder/respond?token={token}&action=not_a_fit"

    portal_line = ""
    if founder_access_token:
        portal_url = f"{web_base}/founder/portal?token={founder_access_token}"
        portal_line = f"\n  🗂  View all candidates for this role  →  {portal_url}\n"

    return (
        f"\n\n{'─' * 50}\n"
        f"Quick reply — no login needed:\n\n"
        f"  ✅  Interested in {candidate_name}  →  {interested_url}\n\n"
        f"  ❌  Not the right fit right now  →  {not_fit_url}\n"
        f"{portal_line}\n"
        f"Replying to this email also works — we read every response.\n"
        f"{'─' * 50}"
    )


class _IntroDelivery:
    """Result of _send_intro: distinguishes direct founder delivery from ops-relay."""
    __slots__ = ("founder_reached", "ops_relayed")

    def __init__(self, *, founder_reached: bool, ops_relayed: bool):
        self.founder_reached = founder_reached
        self.ops_relayed     = ops_relayed

    @property
    def any_sent(self) -> bool:
        return self.founder_reached or self.ops_relayed


async def _send_intro(*, founder_wa: str | None, founder_email: str | None,
                      subject: str, body: str,
                      response_token: str | None = None,
                      founder_access_token: str | None = None,
                      candidate_name: str = "the candidate",
                      job_title: str = "", company: str = "") -> _IntroDelivery:
    """
    Deliver intro to founder.  Returns an _IntroDelivery indicating whether
    the founder was reached directly or whether ops received a relay copy.
    Appends one-click response links if response_token is provided.
    """
    from mitra_api.config import get_settings
    from mitra_api.tools.email import send_email

    s = get_settings()
    ops_email = s.mitra_ops_email.strip()
    founder_reached = False

    # Append one-click response footer to email body
    email_body = body
    if response_token:
        email_body = body + _build_response_links(
            response_token, candidate_name, job_title, company,
            founder_access_token=founder_access_token,
        )

    if founder_wa:
        try:
            from mitra_api.twilio_whatsapp.client import send_whatsapp_reply
            # WhatsApp gets the plain body without the URL footer (too long for WA)
            await send_whatsapp_reply(to_whatsapp_from_value=_to_twilio_wa(founder_wa), body=body)
            log.info("intro sent via WhatsApp to %s", founder_wa)
            founder_reached = True
        except Exception:
            log.exception("WhatsApp intro send failed for %s", founder_wa)

    if founder_email and not founder_reached:
        try:
            founder_reached = await send_email(
                to=founder_email, subject=subject, text=email_body, bcc_ops=True,
            )
        except Exception:
            log.exception("email intro send failed for %s", founder_email)

    # No founder channel — route to ops inbox for manual relay (does NOT count as founder reached)
    ops_relayed = False
    if not founder_reached and ops_email:
        no_channel_note = (
            f"[NO FOUNDER CHANNEL — NEEDS MANUAL RELAY]\n"
            f"founder_email={founder_email!r}  founder_wa={founder_wa!r}\n\n"
            + email_body
        )
        try:
            ops_relayed = await send_email(
                to=ops_email, subject=f"[NEEDS RELAY] {subject}", text=no_channel_note,
            )
            if ops_relayed:
                log.info("intro routed to ops for relay (%s) — no founder channel", ops_email)
        except Exception:
            log.exception("ops relay email failed for %s", ops_email)

    return _IntroDelivery(founder_reached=founder_reached, ops_relayed=ops_relayed)


# ── Public API ────────────────────────────────────────────────────────────────

async def request_intro(
    *,
    candidate_phone: str,
    job_external_id: str,
    why_note: str,
    session: AsyncSession,
    inline_signal_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create an intro record and send the warm intro to the founder.

    ``inline_signal_patch`` is merged into DB-backed signals before the intro gate.
    Ensures salary/name/stack passed on the ``request_intro`` tool call count toward
    the gate even if they were not persisted earlier.

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

    if inline_signal_patch:
        for k, v in inline_signal_patch.items():
            if v is None or v == "" or v == []:
                continue
            signals[k] = v

    # ── Look up job (needed for gate message + fit scoring) ──────────────────
    # Strip the "job_" prefix that interactive_native.py prepends to row_ids
    clean_id = job_external_id.removeprefix("job_").strip()

    _job_q = select(Job).options(selectinload(Job.company_rel))
    job = (await session.execute(
        _job_q.where(Job.external_id == clean_id, Job.status == "active")
    )).scalar_one_or_none()

    if not job:
        try:
            numeric_id = int(clean_id)
            job = (await session.execute(
                _job_q.where(Job.id == numeric_id, Job.status == "active")
            )).scalar_one_or_none()
        except (ValueError, TypeError):
            pass

    if not job:
        log.warning("request_intro: job not found — job_external_id=%r", job_external_id)
        return {"ok": False, "message": f"I couldn't find an active role with id '{job_external_id}'. Please share the job title or company name and I'll look it up."}

    # ── Hard intro gate — block if required signals are missing ───────────────
    missing = _gate_missing(signals)
    if missing:
        missing_str = ", ".join(missing)
        log.info(
            "request_intro: GATE BLOCKED — missing signals %s for candidate=%s job=%s",
            missing, candidate_phone, job_external_id,
        )
        # Record the blocked match decision so we can track gate hit rates
        blocked_match = Match(
            candidate_id=candidate.id,
            job_id=job.id,
            gate_blocked=True,
            gate_missing=missing,
            intro_sent=False,
        )
        session.add(blocked_match)
        await session.commit()
        return {
            "ok": False,
            "needs_more_info": True,
            "missing_signals": missing,
            "message": (
                f"I'd love to send your intro to {job.company} — but to make it strong enough "
                f"that {_founder_contact(job)[0] or 'the founder'} actually responds, I need a few more "
                f"details first: {missing_str}. "
                f"A complete intro is 3× more likely to get a reply. Can you share those now?"
            ),
        }

    # ── Soft signal nudge (non-blocking) ─────────────────────────────────────
    soft_missing = [k for k in _SOFT_SIGNALS if not signals.get(k)]
    if soft_missing:
        log.info(
            "request_intro: proceeding with soft-missing signals %s for candidate=%s",
            soft_missing, candidate_phone,
        )

    # ── Duplicate check — allow strengthen if original was thin ──────────────
    existing_intro = (await session.execute(
        select(Intro).where(Intro.candidate_id == candidate.id, Intro.job_id == job.id)
    )).scalar_one_or_none()

    if existing_intro:
        old_note = existing_intro.intro_note or ""
        signals_now_complete = not bool(_gate_missing(signals))
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
            _fn, _fe, _fw = _founder_contact(job)
            followup_note = (
                f"Hi {_fn or 'there'},\n\n"
                f"Quick follow-up on my earlier intro of {candidate.name or 'the candidate'} "
                f"for the *{job.title}* role. I now have their complete profile and wanted to "
                f"share it properly:\n\n"
                + "\n".join(enriched_note.split("\n")[4:])  # skip the opening preamble, keep profile
            )
            existing_intro.intro_note = enriched_note
            existing_intro.sent_at    = datetime.now(timezone.utc)
            await session.flush()
            subject = f"Follow-up: {candidate.name or 'Candidate'} → {job.title} at {job.company} (full profile)"
            followup_delivery = await _send_intro(
                founder_wa=_fw, founder_email=_fe,
                subject=subject, body=followup_note,
            )
            if followup_delivery.founder_reached:
                existing_intro.status = IntroStatus.sent
            elif followup_delivery.ops_relayed:
                existing_intro.status = IntroStatus.pending_relay
            await session.commit()
            return {
                "ok": True,
                "intro_id": existing_intro.id,
                "strengthened": True,
                "message": (
                    f"I've sent an updated intro to {_fn or 'the founder'} at {job.company} "
                    f"with your complete profile. This one is much stronger — they now have your full "
                    f"background, stack, and what you're looking for."
                ),
                "founder_contacted": followup_delivery.founder_reached,
                "ops_relayed": followup_delivery.ops_relayed,
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

    # ── Compatibility assessment (replaces advisory confidence) ──────────────
    # Phase 2: prefer dedicated founder_profile column; fall back to legacy signals location
    founder_profile = (
        job.founder_profile
        if job.founder_profile
        else (job.signals.get("_founder_profile", {}) if isinstance(job.signals, dict) else {})
    )

    job_dict = {
        "title":          job.title,
        "company":        job.company,
        "stage":          job.stage,
        "sector":         job.sector,
        "stack":          job.stack,
        "salary_min_lpa": job.salary_min_lpa,
        "salary_max_lpa": job.salary_max_lpa,
        "location":       job.location,
        "remote_policy":  job.remote_policy,
    }
    compat = compute_compatibility(signals, job_dict, founder_profile)
    dims   = compat["dimensions"]
    fit    = {
        "salary_fit":   dims["salary_fit"],
        "location_fit": dims["location_fit"],
        "skill_fit":    dims["skill_fit"],
        "overall_fit":  compat["overall_score"],
    }

    log.info(
        "compatibility: candidate=%s job=%s score=%.2f decision=%s risk=%s",
        candidate_phone, job_external_id,
        compat["overall_score"], compat["decision"], compat["risk_flags"],
    )

    # ── Compatibility hard gate — block fundamentally mismatched intros ───────
    if compat["decision"] == "block":
        blocked_match = Match(
            candidate_id=candidate.id,
            job_id=job.id,
            gate_blocked=True,
            gate_missing=["compatibility_block"],
            intro_sent=False,
            compatibility_score=compat["overall_score"],
            compatibility_dimensions=dims,
        )
        session.add(blocked_match)
        await session.commit()
        block_reason = compat["why"] or "This role isn't the right fit based on your profile."
        return {
            "ok": False,
            "needs_more_info": False,
            "message": (
                f"I don't think this intro would serve you well right now — {block_reason} "
                f"I'd rather focus on roles where you're genuinely set up to win. "
                f"Want me to search for better matches?"
            ),
        }

    # ── Compatibility advisory — prompt for more signals before sending ───────
    if compat["decision"] == "collect_more":
        # Don't block — proceed if the candidate explicitly confirms they want to send.
        # The agent will surface the note so they can strengthen first.
        log.info(
            "compatibility collect_more for candidate=%s job=%s — proceeding but noting gaps",
            candidate_phone, job_external_id,
        )

    # ── Build intro message ───────────────────────────────────────────────────
    intro_note = _build_intro(
        candidate=candidate,
        job=job,
        signals=signals,
        why_note=why_note or "Strong technical and cultural fit based on their full profile.",
    )

    # ── Persist intro + match records ─────────────────────────────────────────
    response_token = secrets.token_urlsafe(32)
    intro = Intro(
        candidate_id=candidate.id,
        job_id=job.id,
        status=IntroStatus.sent,
        intro_note=intro_note,
        response_token=response_token,
        sent_at=datetime.now(timezone.utc),
    )
    session.add(intro)
    await session.flush()  # get intro.id

    match_record = Match(
        candidate_id=candidate.id,
        job_id=job.id,
        intro_id=intro.id,
        salary_fit=fit["salary_fit"],
        location_fit=fit["location_fit"],
        skill_fit=fit["skill_fit"],
        overall_fit=fit["overall_fit"],
        compatibility_score=compat["overall_score"],
        compatibility_dimensions=dims,
        decision_policy_version="v1",
        intro_sent=True,
        gate_blocked=False,
    )
    session.add(match_record)
    await session.flush()

    # ── Deliver to founder (+ ops relay fallback) ────────────────────────────
    cand_name = candidate.name or "the candidate"
    subject = f"Intro: {cand_name} → {job.title} at {job.company}"
    _fn, _fe, _fw = _founder_contact(job)
    delivery = await _send_intro(
        founder_wa=_fw,
        founder_email=_fe,
        subject=subject,
        body=intro_note,
        response_token=response_token,
        founder_access_token=getattr(job, "founder_access_token", None),
        candidate_name=cand_name,
        job_title=job.title,
        company=job.company,
    )

    # Status reflects actual delivery: only mark "sent" when the founder received it directly
    if delivery.founder_reached:
        intro.status = IntroStatus.sent
    elif delivery.ops_relayed:
        intro.status = IntroStatus.pending_relay
        log.warning(
            "intro id=%d: no founder channel — routed to ops for manual relay "
            "(founder_wa=%s founder_email=%s)",
            intro.id, _fw, _fe,
        )
    else:
        log.warning(
            "intro id=%d: delivery failed entirely (founder_wa=%s founder_email=%s) — "
            "ops relay also failed; intro is persisted in DB only",
            intro.id, _fw, _fe,
        )

    await session.commit()
    log.info(
        "intro id=%d candidate=%s job=%s company=%s status=%s",
        intro.id, candidate_phone, job_external_id, job.company, intro.status,
    )

    # ── Candidate confirmation email ──────────────────────────────────────────
    # Derive candidate email: web sessions use "web:{email}" as the phone field.
    candidate_email = candidate_phone.removeprefix("web:").strip()
    if "@" in candidate_email:
        try:
            from mitra_api.tools.email import send_email
            candidate_name = candidate.name or "there"
            if delivery.founder_reached:
                delivery_line = (
                    f"Your intro to {_fn or 'the founder'} at {job.company} "
                    f"for the {job.title} role has been sent directly to the founder."
                )
            else:
                delivery_line = (
                    f"Your intro for the {job.title} role at {job.company} has been submitted "
                    f"and is being relayed to the founder by our team. "
                    f"It may take a little longer than usual to get a response."
                )
            confirmation_body = (
                f"Hi {candidate_name},\n\n"
                f"{delivery_line}\n\n"
                f"Here's what was sent on your behalf:\n\n"
                f"{'—' * 40}\n"
                f"{intro_note}\n"
                f"{'—' * 40}\n\n"
                f"You'll hear from us as soon as there's a response.\n\n"
                f"— Mitra"
            )
            await send_email(
                to=candidate_email,
                subject=f"Your intro to {job.company} has been submitted · Mitra",
                text=confirmation_body,
                bcc_ops=True,
            )
        except Exception:
            log.warning("candidate confirmation email failed for %s (non-critical)", candidate_email)

    if delivery.founder_reached:
        result_message = (
            f"Done — I've sent your intro to {_fn or 'the founder'} at {job.company}. "
            f"They typically respond within 24–48 hours. "
            f"Check your inbox — I've sent you a copy of what was shared."
        )
    elif delivery.ops_relayed:
        result_message = (
            f"Your intro for {job.title} at {job.company} has been submitted. "
            f"Our team is relaying it to the founder — it may take a bit longer than usual. "
            f"We'll update you as soon as there's a response."
        )
    else:
        result_message = (
            f"Your intro has been saved but we ran into a delivery issue. "
            f"Our team will follow up with {job.company} directly."
        )

    result: dict[str, Any] = {
        "ok": True,
        "intro_id": intro.id,
        "message": result_message,
        "founder_contacted": delivery.founder_reached,
        "ops_relayed": delivery.ops_relayed,
        "compatibility_score": compat["overall_score"],
        "compatibility_decision": compat["decision"],
    }
    # Surface a note when the intro was sent on collect_more to prompt follow-up collection
    if compat["decision"] == "collect_more" and compat.get("risk_flags"):
        result["confidence_note"] = (
            f"Compatibility score: {int(compat['overall_score'] * 100)}%. "
            f"Gaps: {'; '.join(compat['risk_flags'][:2])}. "
            f"Gathering more signals would improve the response rate."
        )
    return result


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

    clean_id = job_external_id.removeprefix("job_").strip()
    row = (await session.execute(
        select(Intro, Job)
        .join(Job, Intro.job_id == Job.id)
        .where(Intro.candidate_id == candidate.id, Job.external_id == clean_id)
    )).first()
    if not row:
        return {"found": False}

    intro, job = row
    status_messages = {
        IntroStatus.sent:          f"Your intro to {job.company} was sent directly to the founder. Waiting to hear back.",
        IntroStatus.pending_relay: f"Your intro to {job.company} is being relayed to the founder by our team. It may take a little longer than usual.",
        IntroStatus.acknowledged:  f"The founder at {job.company} has seen your intro.",
        IntroStatus.interview:     f"Interview booked with {job.company}.",
        IntroStatus.offer:         f"You have an offer from {job.company}.",
        IntroStatus.hired:         f"Congratulations — you joined {job.company}!",
        IntroStatus.declined:      f"The {job.company} role didn't move forward this time.",
        IntroStatus.ghosted:       f"No reply from {job.company} yet — I'll follow up.",
    }
    return {
        "found": True,
        "status": intro.status,
        "company": job.company,
        "role": job.title,
        "message": status_messages.get(intro.status, f"Status: {intro.status}"),
        "sent_at": intro.sent_at.isoformat() if intro.sent_at else None,
    }
