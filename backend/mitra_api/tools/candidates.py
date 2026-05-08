"""
mitra_api/tools/candidates.py

Upserts candidates and persists their signals to Postgres.
Called by the agent's remember_candidate_signals tool and by the
resume parser when a PDF is uploaded.

This replaces the in-memory signals dict in the old orchestrator.
Signals still flow through the session store (Redis/memory) for
hot-path access, and are durably written here for persistence
across server restarts and for admin visibility.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from mitra_api.db.models import Candidate, CandidateSignal

log = logging.getLogger(__name__)


async def upsert_candidate(phone: str, *, session: AsyncSession) -> Candidate:
    """
    Get or create a candidate by phone number.
    Safe to call on every inbound message — only creates if new.
    """
    result = await session.execute(
        select(Candidate).where(Candidate.phone == phone)
    )
    candidate = result.scalar_one_or_none()

    if candidate is None:
        candidate = Candidate(phone=phone)
        session.add(candidate)
        await session.flush()  # get the id without committing
        log.info("New candidate created: %s", phone)

    return candidate


async def persist_signals(
    phone: str,
    signals: dict[str, Any],
    *,
    session: AsyncSession,
) -> None:
    """
    Upsert candidate signals to Postgres.
    Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE for atomic upsert.

    Called after every remember_candidate_signals tool invocation.
    Also updates top-level Candidate fields if relevant signals are present.
    """
    if not signals:
        return

    candidate = await upsert_candidate(phone, session=session)

    # Upsert each signal key individually
    for key, value in signals.items():
        stmt = pg_insert(CandidateSignal).values(
            candidate_id=candidate.id,
            key=str(key),
            value=value,
        ).on_conflict_do_update(
            constraint="uq_candidate_signal",
            set_={"value": value},
        )
        await session.execute(stmt)

    # Mirror high-value signals into top-level candidate fields for easy querying
    if "candidate_name" in signals and signals["candidate_name"]:
        candidate.name = str(signals["candidate_name"])
    if "current_role" in signals and signals["current_role"]:
        candidate.current_role = str(signals["current_role"])
    if "current_company" in signals and signals["current_company"]:
        candidate.current_company = str(signals["current_company"])
    if "years_experience" in signals and signals["years_experience"]:
        try:
            candidate.years_exp = int(signals["years_experience"])
        except (TypeError, ValueError):
            pass

    await session.commit()
    log.debug("Persisted %d signals for %s", len(signals), phone)


async def get_signals(phone: str, *, session: AsyncSession) -> dict[str, Any]:
    """
    Load all persisted signals for a candidate from Postgres.
    Used to warm the session store after a server restart.
    """
    result = await session.execute(
        select(Candidate).where(Candidate.phone == phone)
    )
    candidate = result.scalar_one_or_none()
    if candidate is None:
        return {}

    sig_result = await session.execute(
        select(CandidateSignal).where(CandidateSignal.candidate_id == candidate.id)
    )
    return {row.key: row.value for row in sig_result.scalars().all()}
