"""
mitra_api/jobs/admin.py

Admin endpoints for managing the jobs database.
Mount with: app.include_router(admin_router)

Endpoints
---------
POST   /admin/jobs           Create a new job (generates embedding automatically)
GET    /admin/jobs           List all jobs with status filter
PUT    /admin/jobs/{id}      Update a job (regenerates embedding if content changes)
DELETE /admin/jobs/{id}      Mark job as expired (soft delete)
POST   /admin/jobs/seed      Bulk-seed from the existing jobs.json file

Authentication
--------------
All endpoints require the X-Admin-Key header matching MITRA_ADMIN_KEY in settings.
Set MITRA_ADMIN_KEY to any strong secret string in your .env file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mitra_api.config import get_settings
from mitra_api.db.engine import get_db, get_session_factory
from mitra_api.db.models import Candidate, Company, Intro, Job, JobEmbedding, JobStatus
from mitra_api.tools.embeddings import EMBEDDING_DIM, embed_text, job_embed_text

log = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin/jobs", tags=["admin"])


# ── AUTH ──────────────────────────────────────────────────────────────────────

async def require_admin(x_admin_key: str = Header(default="")) -> None:
    settings = get_settings()
    expected = getattr(settings, "mitra_admin_key", "").strip()
    if not expected:
        raise HTTPException(503, "MITRA_ADMIN_KEY not configured")
    if x_admin_key != expected:
        raise HTTPException(403, "Invalid admin key")


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class JobIn(BaseModel):
    external_id:    str | None = None
    title:          str
    company:        str
    stage:          str | None = None
    sector:         str | None = None
    location:       str | None = None
    remote_policy:  str | None = None
    employment:     str | None = "full_time"
    salary_min_lpa: int | None = None
    salary_max_lpa: int | None = None
    stack:          list[str] = Field(default_factory=list)
    signals:        list[str] = Field(default_factory=list)
    summary:        str | None = None
    full_jd:        str | None = None
    founder_name:   str | None = None
    founder_email:  str | None = None
    founder_wa:     str | None = None


class JobOut(BaseModel):
    id:             int
    external_id:    str | None
    status:         str
    title:          str
    company:        str
    stage:          str | None
    sector:         str | None
    location:       str | None
    remote_policy:  str | None
    employment:     str | None
    salary_min_lpa: int | None
    salary_max_lpa: int | None
    stack:          list | None
    summary:        str | None
    has_embedding:  bool

    class Config:
        from_attributes = True


# ── HELPERS ───────────────────────────────────────────────────────────────────

async def _generate_and_store_embedding(
    job: Job,
    db: AsyncSession,
    settings=None,
) -> None:
    """Generate embedding for a job and upsert it into job_embeddings."""
    s = settings or get_settings()
    embed_input = job_embed_text({
        "title":   job.title,
        "sector":  job.sector or "",
        "stage":   job.stage or "",
        "stack":   job.stack or [],
        "summary": job.summary or "",
        "location": job.location or "",
    })

    try:
        vector = await embed_text(embed_input)
    except Exception:
        log.exception("Embedding generation failed for job %s — job saved without embedding", job.id)
        return

    # Upsert the embedding row
    result = await db.execute(
        select(JobEmbedding).where(JobEmbedding.job_id == job.id)
    )
    emb = result.scalar_one_or_none()

    if emb is None:
        emb = JobEmbedding(
            job_id=job.id,
            model=getattr(s, "mitra_embedding_provider", "openai"),
            dimensions=EMBEDDING_DIM,
        )
        db.add(emb)
        await db.flush()

    # Store the vector as a pgvector literal via raw SQL
    from sqlalchemy import text
    vec_str = "[" + ",".join(str(x) for x in vector) + "]"
    await db.execute(
        text("UPDATE job_embeddings SET embedding = CAST(:vec AS vector) WHERE id = :id"),
        {"vec": vec_str, "id": emb.id},
    )
    log.info("Embedding stored for job %d (%s)", job.id, job.title)


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@admin_router.post("", response_model=JobOut, dependencies=[Depends(require_admin)])
async def create_job(
    payload: JobIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    """Create a new job listing. Embedding is generated and matching candidates are alerted."""
    job = Job(
        external_id=payload.external_id,
        status=JobStatus.active,
        title=payload.title,
        company=payload.company,
        stage=payload.stage,
        sector=payload.sector,
        location=payload.location,
        remote_policy=payload.remote_policy,
        employment=payload.employment,
        salary_min_lpa=payload.salary_min_lpa,
        salary_max_lpa=payload.salary_max_lpa,
        stack=payload.stack,
        signals=payload.signals,
        summary=payload.summary,
        full_jd=payload.full_jd,
        founder_name=payload.founder_name,
        founder_email=payload.founder_email,
        founder_wa=payload.founder_wa,
    )
    db.add(job)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, f"Job with external_id '{payload.external_id}' already exists")

    await _generate_and_store_embedding(job, db)
    await db.commit()

    result = await db.execute(
        select(Job).options(selectinload(Job.embedding)).where(Job.id == job.id)
    )
    job = result.scalar_one()

    log.info("Job created: id=%d external_id=%s title=%s", job.id, job.external_id, job.title)

    # Alert matching candidates in the background — non-blocking
    from mitra_api.tools.notifications import notify_matching_candidates_bg
    background_tasks.add_task(notify_matching_candidates_bg, job.id)

    return _to_out(job)


@admin_router.get("", response_model=list[JobOut], dependencies=[Depends(require_admin)])
async def list_jobs(
    status: str = "active",
    db: AsyncSession = Depends(get_db),
) -> list[JobOut]:
    """List jobs filtered by status."""
    result = await db.execute(
        select(Job).options(selectinload(Job.embedding))
        .where(Job.status == status).order_by(Job.created_at.desc())
    )
    jobs = result.scalars().all()
    return [_to_out(j) for j in jobs]


@admin_router.put("/{job_id}", response_model=JobOut, dependencies=[Depends(require_admin)])
async def update_job(
    job_id: int,
    payload: JobIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    """Update a job. Regenerates embedding and re-alerts candidates if content changed."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")

    content_changed = (
        job.title   != payload.title   or
        job.stack   != payload.stack   or
        job.summary != payload.summary or
        job.sector  != payload.sector
    )

    # Update fields
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(job, field, value)

    await db.flush()

    if content_changed:
        log.info("Content changed for job %d — regenerating embedding", job_id)
        await _generate_and_store_embedding(job, db)

    await db.commit()

    result = await db.execute(
        select(Job).options(selectinload(Job.embedding)).where(Job.id == job_id)
    )
    job = result.scalar_one()

    # Re-alert candidates when the role content changes materially
    if content_changed:
        from mitra_api.tools.notifications import notify_matching_candidates_bg
        background_tasks.add_task(notify_matching_candidates_bg, job.id)

    return _to_out(job)


@admin_router.delete("/{job_id}", dependencies=[Depends(require_admin)])
async def expire_job(job_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """Soft-delete: mark job as expired. Removes it from search results."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    job.status = JobStatus.expired
    await db.commit()
    log.info("Job %d marked as expired", job_id)
    return {"ok": True, "id": job_id, "status": "expired"}


@admin_router.post("/seed", dependencies=[Depends(require_admin)])
async def seed_from_json(
    json_path: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Bulk-seed jobs from a JSON file.
    Defaults to mitra_api/data/jobs.json — your existing file.
    Skips jobs whose external_id already exists.
    """
    path = Path(json_path) if json_path else (
        Path(__file__).resolve().parent.parent / "data" / "jobs.json"
    )
    if not path.exists():
        raise HTTPException(404, f"File not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise HTTPException(400, "jobs.json must be a JSON array")

    created, skipped = 0, 0
    for row in raw:
        ext_id = str(row.get("id", ""))
        if ext_id:
            exists = await db.execute(select(Job).where(Job.external_id == ext_id))
            if exists.scalar_one_or_none():
                skipped += 1
                continue

        job = Job(
            external_id=ext_id or None,
            status=JobStatus.active,
            title=str(row.get("title", "")),
            company=str(row.get("company", "")),
            location=row.get("location"),
            employment=row.get("employment"),
            stack=row.get("stack") or [],
            signals=list(row.get("signals") or []),
            summary=row.get("summary"),
        )
        db.add(job)
        await db.flush()
        await _generate_and_store_embedding(job, db)
        created += 1

    await db.commit()
    log.info("Seed complete: created=%d skipped=%d", created, skipped)
    return {"created": created, "skipped": skipped}


def _to_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        external_id=job.external_id,
        status=job.status,
        title=job.title,
        company=job.company,
        stage=job.stage,
        sector=job.sector,
        location=job.location,
        remote_policy=job.remote_policy,
        employment=job.employment,
        salary_min_lpa=job.salary_min_lpa,
        salary_max_lpa=job.salary_max_lpa,
        stack=job.stack,
        summary=job.summary,
        has_embedding=job.embedding is not None,
    )


@admin_router.post("/reembed-all", dependencies=[Depends(require_admin)])
async def reembed_all_jobs(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Regenerate embeddings for all active jobs using the current job_embed_text() format.
    Run this after any change to job_embed_text (e.g. adding company name to the embedding).
    Runs in the background — returns immediately with a job count.
    """
    rows = (await db.execute(
        select(Job).where(Job.status == JobStatus.active)
    )).scalars().all()

    job_ids = [j.id for j in rows]
    log.info("reembed-all: queued %d jobs", len(job_ids))

    async def _do_reembed(ids: list[int]) -> None:
        from mitra_api.db.engine import get_session_factory
        factory = get_session_factory()
        ok = err = 0
        for jid in ids:
            try:
                async with factory() as session:
                    job = (await session.execute(
                        select(Job).where(Job.id == jid)
                    )).scalar_one_or_none()
                    if not job:
                        continue
                    embed_input = job_embed_text({
                        "title":   job.title,
                        "company": job.company,
                        "sector":  job.sector,
                        "stage":   job.stage,
                        "stack":   job.stack or [],
                        "summary": job.summary or "",
                        "location": job.location or "",
                    })
                    vec = await embed_text(embed_input)

                    existing = (await session.execute(
                        select(JobEmbedding).where(JobEmbedding.job_id == jid)
                    )).scalar_one_or_none()

                    if existing:
                        existing.embedding = vec
                    else:
                        session.add(JobEmbedding(
                            job_id=jid,
                            embedding=vec,
                            dim=EMBEDDING_DIM,
                        ))
                    await session.commit()
                    ok += 1
            except Exception as exc:
                log.error("reembed-all: job %d failed: %s", jid, exc)
                err += 1
        log.info("reembed-all: done — ok=%d err=%d", ok, err)

    background_tasks.add_task(_do_reembed, job_ids)
    return {"queued": len(job_ids), "status": "running in background"}


# ── METRICS ROUTER ────────────────────────────────────────────────────────────

admin_meta_router = APIRouter(prefix="/admin", tags=["admin"])

_FUNNEL_STAGES = [
    ("sent",         "Intros sent"),
    ("acknowledged", "Interested"),
    ("interview",    "Interview"),
    ("offer",        "Offer"),
    ("hired",        "Hired"),
]


class MetricsSnapshot(BaseModel):
    total_candidates: int
    total_jobs:       int
    active_jobs:      int
    total_intros:     int


class FunnelStage(BaseModel):
    status: str
    label:  str
    count:  int
    pct:    float


class WeeklyPoint(BaseModel):
    week_start:  str
    intros:      int
    interviews:  int
    hires:       int


class TopJob(BaseModel):
    job_id:  int
    title:   str
    company: str
    stage:   str | None
    intros:  int
    hires:   int
    rate:    float


class MetricsResponse(BaseModel):
    snapshot:              MetricsSnapshot
    funnel:                list[FunnelStage]
    by_status:             dict[str, int]
    weekly_trend:          list[WeeklyPoint]
    top_jobs:              list[TopJob]
    response_rate:         float
    ghosted_rate:          float
    avg_days_to_interview: float | None
    avg_days_to_hire:      float | None


@admin_meta_router.get("/metrics", response_model=MetricsResponse, dependencies=[Depends(require_admin)])
async def get_metrics(db: AsyncSession = Depends(get_db)) -> MetricsResponse:
    """Business metrics: intro funnel, weekly trend, top jobs, time-to-hire."""

    # ── Snapshot counts ───────────────────────────────────────────────────────
    total_candidates = (await db.execute(select(func.count(Candidate.id)))).scalar_one() or 0
    total_jobs       = (await db.execute(select(func.count(Job.id)))).scalar_one() or 0
    active_jobs      = (await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.active)
    )).scalar_one() or 0

    # ── Intros by status ──────────────────────────────────────────────────────
    status_rows = (await db.execute(
        select(Intro.status, func.count(Intro.id).label("cnt"))
        .group_by(Intro.status)
    )).all()
    by_status: dict[str, int] = {}
    for row in status_rows:
        key = row.status.value if hasattr(row.status, "value") else str(row.status)
        by_status[key] = int(row.cnt)

    total_intros = sum(by_status.values())
    total_sent   = by_status.get("sent", 0) + by_status.get("acknowledged", 0) + \
                   by_status.get("interview", 0) + by_status.get("offer", 0) + \
                   by_status.get("hired", 0) + by_status.get("declined", 0) + \
                   by_status.get("ghosted", 0)

    # ── Funnel ────────────────────────────────────────────────────────────────
    funnel: list[FunnelStage] = []
    for status_key, label in _FUNNEL_STAGES:
        count = by_status.get(status_key, 0)
        pct   = round(count / total_sent * 100, 1) if total_sent else 0.0
        funnel.append(FunnelStage(status=status_key, label=label, count=count, pct=pct))

    # ── Derived rates ─────────────────────────────────────────────────────────
    engaged      = sum(by_status.get(s, 0) for s in ("acknowledged", "interview", "offer", "hired"))
    ghosted      = by_status.get("ghosted", 0)
    response_rate = round(engaged / total_sent * 100, 1) if total_sent else 0.0
    ghosted_rate  = round(ghosted / total_sent * 100, 1) if total_sent else 0.0

    # ── Weekly trend (last 8 weeks) ───────────────────────────────────────────
    eight_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=8)
    weekly_raw = (await db.execute(
        select(
            func.date_trunc("week", Intro.sent_at).label("week_start"),
            func.count(Intro.id).label("intros"),
            func.sum(case(
                (Intro.status.in_(["interview", "offer", "hired"]), 1), else_=0
            )).label("interviews"),
            func.sum(case(
                (Intro.status == "hired", 1), else_=0
            )).label("hires"),
        )
        .where(Intro.sent_at >= eight_weeks_ago)
        .group_by(text("1"))
        .order_by(text("1"))
    )).all()

    # Fill any missing weeks with zeros
    week_map: dict[str, WeeklyPoint] = {}
    for row in weekly_raw:
        ws = row.week_start.date().isoformat() if hasattr(row.week_start, "date") else str(row.week_start)[:10]
        week_map[ws] = WeeklyPoint(
            week_start=ws,
            intros=int(row.intros or 0),
            interviews=int(row.interviews or 0),
            hires=int(row.hires or 0),
        )

    weekly_trend: list[WeeklyPoint] = []
    cursor = eight_weeks_ago.date()
    # Align to Monday
    cursor = cursor - timedelta(days=cursor.weekday())
    for _ in range(8):
        iso = cursor.isoformat()
        weekly_trend.append(week_map.get(iso, WeeklyPoint(week_start=iso, intros=0, interviews=0, hires=0)))
        cursor += timedelta(weeks=1)

    # ── Top jobs ──────────────────────────────────────────────────────────────
    top_raw = (await db.execute(
        select(
            Job.id, Job.title, Job.company, Job.stage,
            func.count(Intro.id).label("intros"),
            func.sum(case((Intro.status == "hired", 1), else_=0)).label("hires"),
        )
        .join(Intro, Job.id == Intro.job_id)
        .group_by(Job.id, Job.title, Job.company, Job.stage)
        .order_by(func.count(Intro.id).desc())
        .limit(6)
    )).all()

    top_jobs = [
        TopJob(
            job_id=row.id,
            title=row.title,
            company=row.company,
            stage=row.stage,
            intros=int(row.intros or 0),
            hires=int(row.hires or 0),
            rate=round(int(row.hires or 0) / int(row.intros or 1) * 100, 1),
        )
        for row in top_raw
    ]

    # ── Time-to-milestone averages ────────────────────────────────────────────
    avg_interview_raw = (await db.execute(
        select(func.avg(
            func.extract("epoch", Intro.interview_at - Intro.sent_at) / 86400
        ))
        .where(Intro.interview_at.isnot(None), Intro.sent_at.isnot(None))
    )).scalar_one()

    avg_hire_raw = (await db.execute(
        select(func.avg(
            func.extract("epoch", Intro.hired_at - Intro.sent_at) / 86400
        ))
        .where(Intro.hired_at.isnot(None), Intro.sent_at.isnot(None))
    )).scalar_one()

    return MetricsResponse(
        snapshot=MetricsSnapshot(
            total_candidates=total_candidates,
            total_jobs=total_jobs,
            active_jobs=active_jobs,
            total_intros=total_intros,
        ),
        funnel=funnel,
        by_status=by_status,
        weekly_trend=weekly_trend,
        top_jobs=top_jobs,
        response_rate=response_rate,
        ghosted_rate=ghosted_rate,
        avg_days_to_interview=round(float(avg_interview_raw), 1) if avg_interview_raw else None,
        avg_days_to_hire=round(float(avg_hire_raw), 1) if avg_hire_raw else None,
    )


# ── PUBLIC COMPANY FEED ───────────────────────────────────────────────────────

public_router = APIRouter(prefix="/public", tags=["public"])


class CompanyFeedItem(BaseModel):
    id:           int
    name:         str
    stage:        str | None = None
    sector:       str | None = None
    location:     str | None = None
    website:      str | None = None
    founder_name: str | None = None
    amount_usd:   int | None = None
    investors:    list[str]  = []
    active_jobs:  int        = 0
    board_url:    str | None = None
    source_url:   str | None = None
    funded_at:    str | None = None
    created_at:   str


@public_router.get("/companies", response_model=list[CompanyFeedItem])
async def public_companies_feed(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> list[CompanyFeedItem]:
    """Public feed of funded/active companies — powers the /startups page.

    Returns cached DB rows immediately. RSS discovery runs in the background
    when data is empty or stale (>24 h) — never blocks the HTTP response.
    """
    from datetime import datetime, timezone, timedelta

    from mitra_api.db.models import FundedStartup
    from mitra_api.tools.funding_tracker import _sanitize_company_name, run_funding_discovery_pipeline

    async def _load_rows() -> list[FundedStartup]:
        return list((
            await db.execute(
                select(FundedStartup)
                .where(FundedStartup.source == "rss")
                .order_by(FundedStartup.funded_at.desc().nullslast(), FundedStartup.updated_at.desc())
                .limit(200)
            )
        ).scalars().all())

    rows = await _load_rows()

    stale_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
    most_recent = rows[0].updated_at if rows else None
    if most_recent is not None and most_recent.tzinfo is None:
        most_recent = most_recent.replace(tzinfo=timezone.utc)
    is_stale = most_recent is not None and most_recent < stale_threshold

    if not rows:
        # Table empty — run pipeline synchronously so this request returns data.
        # Frontend shows skeletons while waiting (~30–90 s on first populate).
        log.info("public/companies: funded_startups empty — running RSS pipeline now")
        try:
            stats = await run_funding_discovery_pipeline(db)
            log.info("public/companies: pipeline done: %s", stats)
            rows = await _load_rows()
        except Exception:
            log.exception("public/companies: synchronous funding pipeline failed")
    elif is_stale:
        async def _refresh() -> None:
            try:
                from mitra_api.db.engine import get_session_factory
                factory = get_session_factory()
                async with factory() as refresh_db:
                    await run_funding_discovery_pipeline(refresh_db)
            except Exception:
                log.exception("background funding refresh failed")
        background_tasks.add_task(_refresh)

    job_counts: dict[str, int] = {
        name: int(count)
        for name, count in (
            await db.execute(
                select(Job.company, func.count())
                .where(Job.status == JobStatus.active)
                .group_by(Job.company)
            )
        ).all()
    }

    feed: list[CompanyFeedItem] = []
    for row in rows:
        name = _sanitize_company_name(row.name)
        if not name:
            continue
        feed.append(
            CompanyFeedItem(
                id=row.id,
                name=name,
                stage=row.stage,
                sector=row.sector,
                location=row.location,
                website=row.website,
                founder_name=row.founder_name,
                amount_usd=row.amount_usd,
                investors=row.investors or [],
                active_jobs=job_counts.get(name, 0) or job_counts.get(row.name, 0),
                board_url=row.board_url,
                source_url=row.source_url,
                funded_at=row.funded_at.isoformat() if row.funded_at else None,
                created_at=row.discovered_at.isoformat(),
            )
        )
    return feed


# ── COMPANY ADMIN ROUTER ──────────────────────────────────────────────────────

company_router = APIRouter(prefix="/admin/companies", tags=["admin"])


class CompanyIn(BaseModel):
    name:              str
    ashby_identifier:  str | None = None
    greenhouse_slug:   str | None = None
    lever_slug:        str | None = None
    founder_name:      str | None = None
    founder_email:     str | None = None
    founder_wa:        str | None = None
    stage:             str | None = None
    sector:            str | None = None
    website:           str | None = None
    location:          str | None = None
    board_url:         str | None = None
    source:            str | None = None


class CompanyOut(BaseModel):
    id:                   int
    name:                 str
    ashby_identifier:     str | None
    greenhouse_slug:      str | None = None
    lever_slug:           str | None = None
    founder_name:         str | None
    founder_email:        str | None
    stage:                str | None
    sector:               str | None
    website:              str | None
    location:             str | None = None
    board_url:            str | None = None
    source:               str | None = None
    ashby_last_synced_at: str | None
    greenhouse_last_synced_at: str | None = None
    active_jobs:          int = 0

    class Config:
        from_attributes = True


def _company_to_out(company: Company, active_jobs: int = 0) -> CompanyOut:
    ashby_synced = company.ashby_last_synced_at
    gh_synced = company.greenhouse_last_synced_at
    return CompanyOut(
        id=company.id,
        name=company.name,
        ashby_identifier=company.ashby_identifier,
        greenhouse_slug=company.greenhouse_slug,
        lever_slug=company.lever_slug,
        founder_name=company.founder_name,
        founder_email=company.founder_email,
        stage=company.stage,
        sector=company.sector,
        website=company.website,
        location=company.location,
        board_url=company.board_url,
        source=company.source,
        ashby_last_synced_at=ashby_synced.isoformat() if ashby_synced else None,
        greenhouse_last_synced_at=gh_synced.isoformat() if gh_synced else None,
        active_jobs=active_jobs,
    )


@company_router.post("", response_model=CompanyOut, dependencies=[Depends(require_admin)])
async def create_company(
    payload: CompanyIn,
    db: AsyncSession = Depends(get_db),
) -> CompanyOut:
    """Create a new company. Optionally include ashby_identifier to enable Ashby sync."""
    import secrets
    company = Company(
        name=payload.name,
        ashby_identifier=payload.ashby_identifier,
        greenhouse_slug=payload.greenhouse_slug,
        lever_slug=payload.lever_slug,
        founder_name=payload.founder_name,
        founder_email=payload.founder_email,
        founder_wa=payload.founder_wa,
        stage=payload.stage,
        sector=payload.sector,
        website=payload.website,
        location=payload.location,
        board_url=payload.board_url,
        source=payload.source,
        founder_access_token=secrets.token_urlsafe(32),
    )
    db.add(company)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, f"Company with ashby_identifier '{payload.ashby_identifier}' already exists")
    await db.commit()
    log.info("Company created: id=%d name=%s ashby=%s", company.id, company.name, company.ashby_identifier)
    return _company_to_out(company, 0)


@company_router.get("", response_model=list[CompanyOut], dependencies=[Depends(require_admin)])
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[CompanyOut]:
    """List all companies with their active job counts."""
    rows = (await db.execute(
        select(
            Company,
            func.count(Job.id).label("active_jobs"),
        )
        .outerjoin(Job, (Job.company_id == Company.id) & (Job.status == JobStatus.active))
        .group_by(Company.id)
        .order_by(Company.name)
    )).all()
    return [_company_to_out(row.Company, int(row.active_jobs or 0)) for row in rows]


@company_router.put("/{company_id}", response_model=CompanyOut, dependencies=[Depends(require_admin)])
async def update_company(
    company_id: int,
    payload: CompanyIn,
    db: AsyncSession = Depends(get_db),
) -> CompanyOut:
    """Update company details."""
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(404, f"Company {company_id} not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(company, field, value)
    await db.commit()
    return _company_to_out(company, 0)


class FounderContactIn(BaseModel):
    founder_name:  str | None = None
    founder_email: str | None = None
    founder_wa:    str | None = None


@company_router.put(
    "/{company_id}/founder",
    response_model=CompanyOut,
    dependencies=[Depends(require_admin)],
)
async def set_company_founder_contact(
    company_id: int,
    payload: FounderContactIn,
    db: AsyncSession = Depends(get_db),
) -> CompanyOut:
    """
    Set founder contact on a Company and backfill all linked Jobs that still
    have NULL founder fields.  Idempotent — safe to call multiple times.
    """
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(404, f"Company {company_id} not found")

    update = payload.model_dump(exclude_none=True)
    for field, value in update.items():
        setattr(company, field, value)

    # Backfill linked jobs that are missing these fields
    jobs_result = await db.execute(select(Job).where(Job.company_id == company_id))
    backfilled = 0
    for job in jobs_result.scalars().all():
        changed = False
        if payload.founder_name and not job.founder_name:
            job.founder_name = payload.founder_name
            changed = True
        if payload.founder_email and not job.founder_email:
            job.founder_email = payload.founder_email
            changed = True
        if payload.founder_wa and not job.founder_wa:
            job.founder_wa = payload.founder_wa
            changed = True
        if changed:
            backfilled += 1

    await db.commit()
    log.info(
        "founder contact set on company %d (%s); backfilled %d jobs",
        company_id, company.name, backfilled,
    )
    return _company_to_out(company, 0)


@company_router.post(
    "/{company_id}/sync-ashby",
    dependencies=[Depends(require_admin)],
)
async def sync_ashby(
    company_id: int,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Trigger an Ashby job board sync for a company.
    Runs in the background so the request returns immediately.
    Poll GET /admin/companies to see ashby_last_synced_at update.
    """
    company = None
    factory = get_session_factory()
    async with factory() as db:
        company = (await db.execute(
            select(Company).where(Company.id == company_id)
        )).scalar_one_or_none()

    if not company:
        raise HTTPException(404, f"Company {company_id} not found")
    if not company.ashby_identifier:
        raise HTTPException(400, "Company has no ashby_identifier — set it first via PUT /admin/companies/{id}")

    async def _run_sync() -> None:
        from mitra_api.tools.ashby import sync_company_from_ashby
        try:
            result = await sync_company_from_ashby(company_id)
            log.info("ashby-sync triggered via API: company=%d result=%s", company_id, result)
        except Exception:
            log.exception("ashby-sync failed for company %d", company_id)

    background_tasks.add_task(_run_sync)
    return {"ok": True, "company_id": company_id, "message": "Ashby sync started in background"}


@company_router.post(
    "/{company_id}/sync-ashby/wait",
    dependencies=[Depends(require_admin)],
)
async def sync_ashby_wait(company_id: int) -> dict:
    """
    Synchronous Ashby sync — waits for completion and returns the result.
    Use for testing; prefer the background variant in production.
    """
    from mitra_api.tools.ashby import sync_company_from_ashby
    result = await sync_company_from_ashby(company_id)
    return {"ok": True, "company_id": company_id, **result}


@company_router.post(
    "/{company_id}/sync-greenhouse",
    dependencies=[Depends(require_admin)],
)
async def sync_greenhouse(
    company_id: int,
    background_tasks: BackgroundTasks,
) -> dict:
    factory = get_session_factory()
    async with factory() as db:
        company = (await db.execute(
            select(Company).where(Company.id == company_id)
        )).scalar_one_or_none()

    if not company:
        raise HTTPException(404, f"Company {company_id} not found")
    if not company.greenhouse_slug:
        raise HTTPException(400, "Company has no greenhouse_slug — set it via PUT /admin/companies/{id}")

    async def _run_sync() -> None:
        from mitra_api.tools.greenhouse import sync_company_from_greenhouse
        try:
            result = await sync_company_from_greenhouse(company_id)
            log.info("greenhouse-sync via API: company=%d result=%s", company_id, result)
        except Exception:
            log.exception("greenhouse-sync failed for company %d", company_id)

    background_tasks.add_task(_run_sync)
    return {"ok": True, "company_id": company_id, "message": "Greenhouse sync started in background"}


@company_router.post(
    "/{company_id}/sync-greenhouse/wait",
    dependencies=[Depends(require_admin)],
)
async def sync_greenhouse_wait(company_id: int) -> dict:
    from mitra_api.tools.greenhouse import sync_company_from_greenhouse
    result = await sync_company_from_greenhouse(company_id)
    return {"ok": True, "company_id": company_id, **result}


# ── FUNDING / ATS DISCOVERY ROUTER ───────────────────────────────────────────

funding_router = APIRouter(prefix="/admin/funding", tags=["admin"])


@funding_router.get("/llm-check", dependencies=[Depends(require_admin)])
async def funding_llm_check() -> dict:
    """
    One-shot LLM connectivity test for the funding extraction pipeline.
    Use after deploy to confirm OPENAI_API_KEY and extraction model work on Railway.
    """
    from mitra_api.config import get_settings
    from mitra_api.llm.factory import get_llm_adapter
    from mitra_api.tools.funding_tracker import RssItem, _extract_batch

    s = get_settings()
    sample = RssItem(
        title="Razorpay raises $200M in Series F funding round",
        description="Indian fintech Razorpay closed a Series F round led by major investors.",
        link="https://example.com/razorpay-series-f",
        pub_date=None,
    )
    try:
        adapter = get_llm_adapter(s)
        events = await _extract_batch(adapter, s.mitra_llm_cheap_model, [sample])
        return {
            "ok": True,
            "provider": s.mitra_llm_provider,
            "extraction_model": s.mitra_llm_cheap_model,
            "sample_events": len(events),
            "first_event": events[0] if events else None,
        }
    except Exception as exc:
        log.exception("funding LLM check failed")
        return {
            "ok": False,
            "provider": s.mitra_llm_provider,
            "extraction_model": s.mitra_llm_cheap_model,
            "error": str(exc),
        }


@funding_router.post("/scan", dependencies=[Depends(require_admin)])
async def scan_funding(dry_run: bool = False) -> dict:
    """
    Fetch RSS funding headlines, extract events via LLM, upsert funded_startups.
    Provider/model controlled by MITRA_LLM_PROVIDER and MITRA_LLM_CHEAP_MODEL.
    """
    from mitra_api.db.engine import get_session_factory
    from mitra_api.tools.funding_tracker import run_funding_discovery_pipeline

    factory = get_session_factory()
    async with factory() as db:
        return await run_funding_discovery_pipeline(db, dry_run=dry_run)


@funding_router.post("/enrich", dependencies=[Depends(require_admin)])
async def enrich_funding_metadata() -> dict:
    """
    Fill missing founder_name and website for existing funded_startups rows.
    Uses LLM batch enrichment; falls back to Tavily web search if TAVILY_API_KEY is set.
    """
    from mitra_api.db.engine import get_session_factory
    from mitra_api.tools.funding_tracker import (
        _acquire_pipeline_db_lock,
        _pg_advisory_unlock,
        enrich_funded_startups_metadata,
    )

    factory = get_session_factory()
    async with factory() as db:
        await _acquire_pipeline_db_lock(db)
        try:
            stats = await enrich_funded_startups_metadata()
        finally:
            await _pg_advisory_unlock(db)
    return {"ok": True, **stats}


@funding_router.post("/discover-ats", dependencies=[Depends(require_admin)])
async def discover_company_ats(company_name: str) -> dict:
    from mitra_api.tools.funding_tracker import discover_ats

    result = await discover_ats(company_name)
    return result or {"ats": None, "message": f"No ATS found for {company_name}"}


@funding_router.get("/queue", dependencies=[Depends(require_admin)])
async def funding_outreach_queue(db: AsyncSession = Depends(get_db)) -> list[dict]:
    from mitra_api.tools.funding_tracker import get_outreach_queue
    return await get_outreach_queue(db)


@admin_router.post("/sync-all", dependencies=[Depends(require_admin)])
async def sync_all_ats(background_tasks: BackgroundTasks) -> dict:
    """Sync all companies with Ashby or Greenhouse identifiers."""

    async def _run() -> None:
        from mitra_api.tools.ashby import sync_all_companies as sync_ashby_all
        from mitra_api.tools.greenhouse import sync_all_greenhouse_companies
        from mitra_api.tools.lever import sync_all_lever_companies
        try:
            ashby = await sync_ashby_all()
            gh = await sync_all_greenhouse_companies()
            lever = await sync_all_lever_companies()
            log.info("sync-all done ashby=%s greenhouse=%s lever=%s", ashby, gh, lever)
        except Exception:
            log.exception("sync-all failed")

    background_tasks.add_task(_run)
    return {"ok": True, "message": "Full ATS sync started in background"}


@admin_router.post("/sync-greenhouse", dependencies=[Depends(require_admin)])
async def sync_greenhouse_by_slug(
    company_name: str,
    slug: str,
    stage: str = "",
    sector: str = "",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create-or-update a company by Greenhouse slug and sync immediately."""
    import secrets
    from mitra_api.tools.greenhouse import sync_company_from_greenhouse

    company = (await db.execute(
        select(Company).where(Company.name.ilike(company_name))
    )).scalar_one_or_none()

    if not company:
        company = Company(
            name=company_name,
            greenhouse_slug=slug,
            stage=stage or None,
            sector=sector or None,
            board_url=f"https://boards.greenhouse.io/{slug}",
            source="manual",
            founder_access_token=secrets.token_urlsafe(32),
        )
        db.add(company)
        await db.flush()
    else:
        company.greenhouse_slug = slug
        if stage:
            company.stage = stage
        if sector:
            company.sector = sector

    await db.commit()
    result = await sync_company_from_greenhouse(company.id)
    return {"ok": True, "company_id": company.id, **result}
