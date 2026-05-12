"""Candidate web chat endpoint — powers the in-app chat UI."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from mitra_api.agent.orchestrator import run_agent_turn
from mitra_api.agent.session_store import AgentSessionStore, build_session_store
from mitra_api.config import Settings, get_settings
from mitra_api.db.engine import get_session_factory
from mitra_api.tools.intros import request_intro
from mitra_api.db.models import Candidate, Intro, Job

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
    why: str = ""    # personalised 1-2 sentence fit explanation from LLM reranker


class CandidateChatResponse(BaseModel):
    reply: str
    job_cards: list[JobCard]


class FullJobCard(BaseModel):
    id: int
    external_id: str | None = None
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
    ids: str = Query(..., description="Comma-separated job IDs e.g. 1,2,3 or external_ids"),
    settings: Settings = Depends(get_settings),
) -> list[FullJobCard]:
    """Fetch full job details by numeric DB id or string external_id (row_id from native list)."""
    from sqlalchemy import select, or_
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job as JobModel

    # Strip the "job_" prefix that interactive_native.py prepends to row_ids
    raw_ids = [i.strip().removeprefix("job_") for i in ids.split(",") if i.strip()]

    numeric_ids: list[int] = []
    string_ids: list[str] = []
    for r in raw_ids:
        try:
            numeric_ids.append(int(r))
        except ValueError:
            if r:
                string_ids.append(r)

    if not numeric_ids and not string_ids:
        return []

    factory = get_session_factory()
    async with factory() as db:
        clauses = []
        if numeric_ids:
            clauses.append(JobModel.id.in_(numeric_ids))
        if string_ids:
            clauses.append(JobModel.external_id.in_(string_ids))
        rows = (await db.execute(
            select(JobModel).where(or_(*clauses))
        )).scalars().all()

    def _make_card(job: JobModel) -> FullJobCard:
        stack = [str(s) for s in job.stack] if isinstance(job.stack, list) else []
        sigs  = job.signals if isinstance(job.signals, dict) else {}
        return FullJobCard(
            id=job.id, external_id=job.external_id,
            title=job.title, company=job.company,
            stage=job.stage, sector=job.sector, location=job.location,
            remote_policy=job.remote_policy, employment=job.employment,
            salary_min_lpa=job.salary_min_lpa, salary_max_lpa=job.salary_max_lpa,
            stack=stack, summary=job.summary, signals=sigs,
        )

    result = [_make_card(j) for j in rows]

    # Preserve requested order: numeric IDs first, then string external_ids
    num_order = {nid: i for i, nid in enumerate(numeric_ids)}
    str_order = {sid: i + len(numeric_ids) for i, sid in enumerate(string_ids)}
    result.sort(key=lambda j: num_order.get(j.id, str_order.get(j.id, 999)))
    return result


class IntroRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=200)
    job_id: str     = Field(..., min_length=1, max_length=200)
    why_note: str   = Field(default="", max_length=600)


class IntroResponse(BaseModel):
    ok: bool
    message: str
    intro_id: int | None = None
    founder_contacted: bool = False
    already_sent: bool = False
    confirmation_sent: bool = False


@router.post("/intro", response_model=IntroResponse)
async def request_candidate_intro(body: IntroRequest) -> IntroResponse:
    """
    Trigger a warm intro from the web matches page.
    The candidate is identified by their NextAuth email (session_id).
    Signals already persisted from the chat session are used to enrich the intro.
    """
    sid = f"web:{body.session_id}"
    factory = get_session_factory()
    async with factory() as db:
        result = await request_intro(
            candidate_phone=sid,
            job_external_id=body.job_id,
            why_note=body.why_note,
            session=db,
        )

    return IntroResponse(
        ok=bool(result.get("ok", False)),
        message=str(result.get("message", "Something went wrong — please try again.")),
        intro_id=result.get("intro_id"),
        founder_contacted=bool(result.get("founder_contacted", False)),
        already_sent=not result.get("ok", True) and "already sent" in str(result.get("message", "")),
    )


class IntroSummary(BaseModel):
    intro_id: int
    job_id: int
    job_title: str
    company: str
    status: str
    sent_at: str | None = None   # ISO-8601
    interview_details: dict | None = None  # {"scheduled_at","format","link","notes"}
    offer_details: dict | None = None      # {"salary_lpa","equity_percent","start_date","notes"}


@router.get("/intros", response_model=list[IntroSummary])
async def list_candidate_intros(
    session_id: str = Query(..., description="Candidate email (used as session_id)"),
) -> list[IntroSummary]:
    """Return all intros that have been sent for this web candidate, newest first."""
    from sqlalchemy import select

    sid = f"web:{session_id}"
    factory = get_session_factory()
    async with factory() as db:
        candidate = (await db.execute(
            select(Candidate).where(Candidate.phone == sid)
        )).scalar_one_or_none()

        if not candidate:
            return []

        rows = (await db.execute(
            select(Intro, Job)
            .join(Job, Intro.job_id == Job.id)
            .where(Intro.candidate_id == candidate.id)
            .order_by(Intro.requested_at.desc())
        )).all()

    return [
        IntroSummary(
            intro_id=intro.id,
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            status=str(intro.status),
            sent_at=intro.sent_at.isoformat() if intro.sent_at else None,
            interview_details=intro.interview_details or None,
            offer_details=intro.offer_details or None,
        )
        for intro, job in rows
    ]


_RESTART_PHRASES = (
    "start fresh", "start again", "start over", "restart", "from scratch",
    "new search", "reset", "begin again", "let's start fresh", "start new",
)


def _is_restart_intent(text: str) -> bool:
    t = text.lower()
    return any(phrase in t for phrase in _RESTART_PHRASES)


@router.post("/chat", response_model=CandidateChatResponse)
async def candidate_chat(
    body: CandidateChatRequest,
    settings: Settings = Depends(get_settings),
) -> CandidateChatResponse:
    store = _get_store(settings)
    # "web:" prefix keeps web sessions separate from WhatsApp sessions
    sid = f"web:{body.session_id}"
    is_init = not body.message.strip()
    fresh_start = False

    if is_init:
        # On page load: warm session store signals from DB if Redis is cold (new device / TTL expired)
        if settings.mitra_database_url:
            try:
                from mitra_api.db.engine import get_session_factory as _sf
                from mitra_api.tools.candidates import get_signals as get_db_signals
                redis_signals = await store.get_signals(sid)
                if not redis_signals:
                    factory = _sf()
                    async with factory() as _db:
                        db_signals = await get_db_signals(sid, session=_db)
                    if db_signals:
                        await store.merge_signals(sid, db_signals)
                        log.info("warmed session %s with %d DB signals", sid, len(db_signals))
            except Exception:
                log.warning("could not warm signals from DB for %s (non-critical)", sid, exc_info=True)

        # Return last assistant message if session exists, else trigger greeting
        transcript = await store.get_transcript(sid)
        if transcript:
            for msg in reversed(transcript):
                if msg.role == "assistant":
                    content = msg.content or ""
                    # If the last message is a raw WhatsApp-formatted shortlist, replace it with
                    # a clean web-friendly welcome-back line. The web UI shows a dedicated
                    # "matches ready" banner, so the raw card text isn't needed here.
                    from mitra_api.whatsapp.job_cards import WHATSAPP_SHORTLIST_MARKER
                    _WA_NOISE = (WHATSAPP_SHORTLIST_MARKER, "―――――――――――", "1 of ", "2 of ", "3 of ")
                    if any(marker in content for marker in _WA_NOISE):
                        first = body.user_name.split()[0] if body.user_name else None
                        greeting = (
                            f"Welcome back{', ' + first if first else ''}! "
                            "Your shortlist is ready — I've curated the best-fit roles for you. "
                            "Tap \"View shortlist\" to review them, or keep chatting if you'd like to adjust anything."
                        )
                        return CandidateChatResponse(reply=greeting, job_cards=[])
                    return CandidateChatResponse(reply=content, job_cards=[])
        name_part = f" The candidate's name is {body.user_name}." if body.user_name else ""
        user_text = (
            f"[CONVERSATION START on the Mitra web app.{name_part} "
            "Greet them warmly by name if you have it, and ask what brings them here.]"
        )
    else:
        user_text = body.message.strip()

        # Detect explicit "start from scratch" intent — clear chat history so the
        # agent starts a clean search conversation without re-firing old intros.
        if _is_restart_intent(user_text):
            await store.clear_transcript(sid)
            fresh_start = True
            log.info("restart intent detected for %s — transcript cleared", sid)

    turn = await run_agent_turn(
        whatsapp_sender_id=sid,
        user_text=user_text,
        sessions=store,
        settings=settings,
        fresh_start=fresh_start,
    )

    job_cards = [
        JobCard(
            id=r.row_id,
            title=r.title,
            description=r.description,
            why=turn.job_whys.get(r.row_id) or turn.job_whys.get(r.row_id.replace("job_", "")) or "",
        )
        for r in turn.native_list_rows
    ]

    return CandidateChatResponse(
        reply=turn.history_assistant_text,
        job_cards=job_cards,
    )
