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

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mitra_api.config import get_settings
from mitra_api.db.engine import get_db
from mitra_api.db.models import Job, JobEmbedding, JobStatus
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
async def create_job(payload: JobIn, db: AsyncSession = Depends(get_db)) -> JobOut:
    """Create a new job listing. Embedding is generated automatically."""
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
    await db.flush()

    await _generate_and_store_embedding(job, db)
    await db.commit()
    await db.refresh(job)

    log.info("Job created: id=%d external_id=%s title=%s", job.id, job.external_id, job.title)
    return _to_out(job)


@admin_router.get("", response_model=list[JobOut], dependencies=[Depends(require_admin)])
async def list_jobs(
    status: str = "active",
    db: AsyncSession = Depends(get_db),
) -> list[JobOut]:
    """List jobs filtered by status."""
    result = await db.execute(
        select(Job).where(Job.status == status).order_by(Job.created_at.desc())
    )
    jobs = result.scalars().all()
    return [_to_out(j) for j in jobs]


@admin_router.put("/{job_id}", response_model=JobOut, dependencies=[Depends(require_admin)])
async def update_job(
    job_id: int,
    payload: JobIn,
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    """Update a job. Regenerates embedding if title, stack, or summary changed."""
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
    await db.refresh(job)
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
