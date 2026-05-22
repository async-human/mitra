"""
mitra_api/tools/lever.py

Lever public job board sync — no authentication required.

  GET https://api.lever.co/v0/postings/{slug}?mode=json

Idempotent sync keyed on external_id = "lever:{posting-id}".
"""

from __future__ import annotations

import html as html_lib
import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Any

import httpx

log = logging.getLogger(__name__)

LEVER_API = "https://api.lever.co/v0/postings/{slug}?mode=json"
_STALE_DAYS = 90

_ENGINEERING_TITLE_KEYWORDS = {
    "engineer", "developer", "backend", "frontend", "fullstack",
    "full stack", "full-stack", "ml ", "machine learning",
    "data engineer", "data scientist", "platform", "infrastructure",
    "devops", "sre", "reliability", "software", "android", "ios",
    "mobile", "python", "golang", "java", "architect", "tech lead",
    "technical lead", "engineering manager", "em ", "staff engineer",
    "principal engineer", "founding engineer", "ai engineer",
    "applied scientist", "research engineer", "product engineer",
}

_INDIA_LOCATION_KEYWORDS = {
    "india", "bengaluru", "bangalore", "mumbai", "hyderabad",
    "delhi", "noida", "gurgaon", "gurugram", "pune", "chennai",
    "kolkata", "remote", "anywhere", "flexible", "worldwide",
}


def _strip_html(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"</(p|li|div|h[1-6]|tr)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _is_engineering_role(title: str, department: str = "") -> bool:
    t = f"{title} {department}".lower()
    return any(kw in t for kw in _ENGINEERING_TITLE_KEYWORDS)


def _is_india_location(location: str) -> bool:
    if not location:
        return True
    loc = location.lower()
    return any(kw in loc for kw in _INDIA_LOCATION_KEYWORDS)


async def fetch_lever_jobs(slug: str) -> list[dict[str, Any]]:
    url = LEVER_API.format(slug=slug)
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    return data if isinstance(data, list) else []


def _parse_posting(raw: dict[str, Any], slug: str) -> dict[str, Any] | None:
    title = (raw.get("text") or "").strip()
    categories = raw.get("categories") or {}
    location = categories.get("location") or ""
    if not location and categories.get("allLocations"):
        location = categories["allLocations"][0]
    department = categories.get("department") or categories.get("team") or ""
    job_id = raw.get("id")

    if not title or not job_id:
        return None
    if not _is_engineering_role(title, department):
        return None
    if not _is_india_location(location):
        return None

    created_ms = raw.get("createdAt")
    updated_at = None
    if created_ms:
        try:
            updated_at = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass

    potentially_stale = False
    if updated_at:
        age_days = (datetime.now(timezone.utc) - updated_at).days
        if age_days > _STALE_DAYS:
            potentially_stale = True

    full_jd = raw.get("descriptionPlain") or ""
    if not full_jd and raw.get("description"):
        full_jd = _strip_html(raw["description"])
    summary = ""
    if full_jd:
        lines = [ln.strip() for ln in full_jd.splitlines() if ln.strip()]
        summary = lines[0][:300] if lines else ""

    hosted_url = raw.get("hostedUrl") or f"https://jobs.lever.co/{slug}/{job_id}"

    return {
        "external_id": f"lever:{job_id}",
        "title": title,
        "location": location or "India",
        "full_jd": full_jd[:8000],
        "summary": summary or None,
        "signals": {
            "source": "lever",
            "source_slug": slug,
            "lever_url": hosted_url,
            "updated_at_source": updated_at.isoformat() if updated_at else None,
            "potentially_stale": potentially_stale,
            "department": department or None,
        },
    }


async def sync_company_from_lever(company_id: int) -> dict[str, Any]:
    """Fetch Lever board for one company and upsert India engineering roles."""
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Company, Job, JobStatus
    from mitra_api.jobs.admin import _generate_and_store_embedding
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as db:
        company: Company | None = (
            await db.execute(select(Company).where(Company.id == company_id))
        ).scalar_one_or_none()

        if not company:
            raise ValueError(f"Company {company_id} not found")
        if not company.lever_slug:
            raise ValueError(f"Company {company_id} has no lever_slug set")

        slug = company.lever_slug
        log.info("lever-sync: company=%d (%s) slug=%s", company_id, company.name, slug)

        try:
            raw_jobs = await fetch_lever_jobs(slug)
        except httpx.HTTPStatusError as exc:
            log.error("lever-sync: HTTP %s for company %d", exc.response.status_code, company_id)
            raise
        except Exception as exc:
            log.error("lever-sync: fetch failed for company %d: %s", company_id, exc)
            raise

        seen: set[str] = set()
        created = updated = expired = filtered = stale = errors = 0

        for raw in raw_jobs:
            parsed = _parse_posting(raw, slug)
            if parsed is None:
                filtered += 1
                continue

            ext_id = parsed["external_id"]
            seen.add(ext_id)
            if parsed["signals"].get("potentially_stale"):
                stale += 1

            try:
                existing: Job | None = (
                    await db.execute(select(Job).where(Job.external_id == ext_id))
                ).scalar_one_or_none()

                if existing:
                    existing.title = parsed["title"]
                    existing.location = parsed["location"]
                    existing.full_jd = parsed["full_jd"] or existing.full_jd
                    existing.summary = parsed["summary"] or existing.summary
                    existing.status = JobStatus.active
                    prev = existing.signals if isinstance(existing.signals, dict) else {}
                    existing.signals = {**prev, **parsed["signals"]}
                    updated += 1
                    if not existing.embedding:
                        await _generate_and_store_embedding(existing, db)
                else:
                    job = Job(
                        external_id=ext_id,
                        company_id=company_id,
                        company=company.name,
                        title=parsed["title"],
                        location=parsed["location"],
                        stage=company.stage,
                        sector=company.sector,
                        full_jd=parsed["full_jd"],
                        summary=parsed["summary"],
                        founder_name=company.founder_name,
                        founder_email=company.founder_email,
                        founder_wa=company.founder_wa,
                        founder_access_token=secrets.token_urlsafe(32),
                        stack=[],
                        signals=parsed["signals"],
                        status=JobStatus.active,
                    )
                    db.add(job)
                    await db.flush()
                    await _generate_and_store_embedding(job, db)
                    created += 1
            except Exception as exc:
                log.error("lever-sync: error on %s: %s", ext_id, exc)
                errors += 1

        active_jobs: list[Job] = (
            await db.execute(
                select(Job).where(
                    Job.company_id == company_id,
                    Job.external_id.like("lever:%"),
                    Job.status == JobStatus.active,
                )
            )
        ).scalars().all()

        for job in active_jobs:
            if job.external_id not in seen:
                job.status = JobStatus.filled
                expired += 1

        company.lever_last_synced_at = datetime.now(timezone.utc)
        if not company.board_url:
            company.board_url = f"https://jobs.lever.co/{slug}"
        await db.commit()

    log.info(
        "lever-sync done: company=%d created=%d updated=%d expired=%d "
        "filtered=%d stale=%d errors=%d",
        company_id, created, updated, expired, filtered, stale, errors,
    )
    return {
        "created": created,
        "updated": updated,
        "expired": expired,
        "filtered": filtered,
        "stale": stale,
        "errors": errors,
    }


async def sync_all_lever_companies() -> dict[str, Any]:
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Company
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as db:
        companies: list[Company] = (
            await db.execute(
                select(Company).where(Company.lever_slug.isnot(None))
            )
        ).scalars().all()

    results: dict[str, Any] = {}
    for company in companies:
        try:
            results[company.name] = await sync_company_from_lever(company.id)
        except Exception as exc:
            results[company.name] = {"error": str(exc)}
    return results
