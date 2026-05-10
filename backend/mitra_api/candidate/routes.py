"""Candidate web chat endpoint — powers the in-app chat UI."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from mitra_api.agent.orchestrator import run_agent_turn
from mitra_api.agent.session_store import AgentSessionStore, build_session_store
from mitra_api.config import Settings, get_settings

log = logging.getLogger(__name__)

router = APIRouter(prefix="/candidate", tags=["candidate"])

_store: AgentSessionStore | None = None


def _get_store(settings: Settings) -> AgentSessionStore:
    global _store
    if _store is None:
        _store = build_session_store(settings)
    return _store


class CandidateChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=200)
    message: str = Field(default="", max_length=4000)
    user_name: str | None = Field(default=None, max_length=100)


class JobCard(BaseModel):
    id: str
    title: str
    description: str  # "Company · 95% fit · Python · Remote"


class CandidateChatResponse(BaseModel):
    reply: str
    job_cards: list[JobCard]


class FullJobCard(BaseModel):
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
    stack: list[str]
    summary: str | None
    signals: dict[str, Any]


@router.get("/jobs", response_model=list[FullJobCard])
async def get_jobs_by_ids(
    ids: str = Query(..., description="Comma-separated job IDs e.g. 1,2,3"),
    settings: Settings = Depends(get_settings),
) -> list[FullJobCard]:
    """Fetch full job details for given numeric IDs (from native_list_rows row_id)."""
    raw_ids = [i.strip().lstrip("job_") for i in ids.split(",") if i.strip()]
    numeric_ids = []
    for r in raw_ids:
        try:
            numeric_ids.append(int(r))
        except ValueError:
            pass
    if not numeric_ids:
        return []

    from sqlalchemy import select
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job

    factory = get_session_factory()
    async with factory() as db:
        rows = (await db.execute(
            select(Job).where(Job.id.in_(numeric_ids))
        )).scalars().all()

    result = []
    for job in rows:
        stack: list[str] = []
        if isinstance(job.stack, list):
            stack = [str(s) for s in job.stack]
        sigs: dict = {}
        if isinstance(job.signals, dict):
            sigs = job.signals
        result.append(FullJobCard(
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
            stack=stack,
            summary=job.summary,
            signals=sigs,
        ))
    # preserve the order of the requested IDs
    order = {nid: i for i, nid in enumerate(numeric_ids)}
    result.sort(key=lambda j: order.get(j.id, 99))
    return result


@router.post("/chat", response_model=CandidateChatResponse)
async def candidate_chat(
    body: CandidateChatRequest,
    settings: Settings = Depends(get_settings),
) -> CandidateChatResponse:
    store = _get_store(settings)
    # "web:" prefix keeps web sessions separate from WhatsApp sessions
    sid = f"web:{body.session_id}"
    is_init = not body.message.strip()

    if is_init:
        # On page load: return last assistant message if session exists, else trigger greeting
        transcript = await store.get_transcript(sid)
        if transcript:
            for msg in reversed(transcript):
                if msg.role == "assistant":
                    return CandidateChatResponse(reply=msg.content, job_cards=[])
        name_part = f" The candidate's name is {body.user_name}." if body.user_name else ""
        user_text = (
            f"[CONVERSATION START on the Mitra web app.{name_part} "
            "Greet them warmly by name if you have it, and ask what brings them here.]"
        )
    else:
        user_text = body.message.strip()

    turn = await run_agent_turn(
        whatsapp_sender_id=sid,
        user_text=user_text,
        sessions=store,
        settings=settings,
    )

    job_cards = [
        JobCard(id=r.row_id, title=r.title, description=r.description)
        for r in turn.native_list_rows
    ]

    return CandidateChatResponse(
        reply=turn.history_assistant_text,
        job_cards=job_cards,
    )
