"""Load introduction / offer facts from Postgres for web candidates (offer coaching)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from mitra_api.db.models import Candidate, Intro, Job

log = logging.getLogger(__name__)


def _fmt_offer_detail(od: dict[str, Any] | None) -> list[str]:
    if not od:
        return []
    lines: list[str] = []
    if od.get("salary_lpa") is not None:
        lines.append(f"Salary (LPA CTC): ₹{od['salary_lpa']}L")
    if od.get("equity_percent") is not None:
        lines.append(f"Equity: {od['equity_percent']}%")
    if od.get("start_date"):
        lines.append(f"Start date: {od['start_date']}")
    if od.get("notes"):
        lines.append(f"Notes from founder: {od['notes']}")
    return lines


def _fmt_interview(iv: dict[str, Any] | None) -> list[str]:
    if not iv:
        return []
    out: list[str] = []
    if iv.get("scheduled_at"):
        out.append(f"Interview scheduled: {iv['scheduled_at']}")
    if iv.get("format"):
        out.append(f"Format: {iv['format']}")
    return out


async def build_offer_coaching_context_block(
    whatsapp_sender_id: str,
    db_factory: Any,
) -> str | None:
    """
    Build a system-message block with offer-stage intros and key pipeline rows.
    Returns None only if the candidate record is missing or DB fails (caller may use a fallback).
    """
    if not whatsapp_sender_id.startswith("web:"):
        return None

    try:
        async with db_factory() as db:
            candidate = (
                await db.execute(select(Candidate).where(Candidate.phone == whatsapp_sender_id))
            ).scalar_one_or_none()
            if not candidate:
                return None

            rows = (
                await db.execute(
                    select(Intro, Job)
                    .join(Job, Intro.job_id == Job.id)
                    .where(Intro.candidate_id == candidate.id)
                    .order_by(Intro.requested_at.desc())
                )
            ).all()
    except Exception:
        log.exception("build_offer_coaching_context_block failed for %s", whatsapp_sender_id)
        return None

    if not rows:
        return (
            "[CANDIDATE PIPELINE — FACTS ON FILE (Mitra DB)]\n"
            "No introductions are stored for this account yet."
        )

    offer_chunks: list[str] = []
    pipeline_chunks: list[str] = []

    for intro, job in rows:
        st = str(intro.status)
        sent = intro.sent_at.isoformat() if intro.sent_at else "unknown"
        head = (
            f"- {job.company} — {job.title} (intro id {intro.id}, status: {st}, intro sent: {sent})"
        )
        if st == "offer":
            od = intro.offer_details if isinstance(intro.offer_details, dict) else None
            det = _fmt_offer_detail(od)
            if det:
                offer_chunks.append(head + "\n  " + "\n  ".join(det))
            else:
                offer_chunks.append(
                    head + "\n  (No structured offer fields in Mitra — founder may have extended verbally only.)"
                )
        elif st in ("interview", "acknowledged", "sent", "ghosted"):
            iv = intro.interview_details if isinstance(intro.interview_details, dict) else None
            extra = _fmt_interview(iv)
            pipeline_chunks.append(
                head + (("\n  " + " · ".join(extra)) if extra else "")
            )

    parts: list[str] = [
        "[CANDIDATE PIPELINE — FACTS ON FILE (Mitra DB)]",
        "These rows are what the founder logged in Mitra (intro status, offer forms, interview slots). "
        "Lead with this when coaching — do not ask the candidate to repeat numbers that already appear here "
        "(confirm or update if they say something different).",
        "",
    ]
    if offer_chunks:
        parts.append("Offer stage (structured details Mitra has):")
        parts.extend(offer_chunks)
        parts.append("")
    if pipeline_chunks:
        parts.append("Other introductions (recent, for context):")
        parts.extend(pipeline_chunks[:6])
        parts.append("")

    return "\n".join(parts).strip()
