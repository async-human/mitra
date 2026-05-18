"""
mitra_api/tools/ashby.py

Ashby public job board sync (Level 1 — no auth required).

Ashby hosts a public Posting API for every company on the platform.
Given a company's board identifier (their Ashby subdomain slug), we can
fetch all active job postings without any API key or OAuth flow.

API reference: https://developers.ashbyhq.com/reference/posting-jobboard
Endpoint: POST https://api.ashbyhq.com/posting-api/job-board
Body:     {"boardIdentifier": "<slug>"}

The sync is idempotent:
  - New postings are INSERTed with external_id = "ashby:<posting-id>"
  - Existing postings are UPDATEd (title, location, full_jd, summary)
  - Postings no longer returned by Ashby are marked as filled/expired
"""

from __future__ import annotations

import html as html_lib
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

log = logging.getLogger(__name__)

ASHBY_POSTING_API = "https://api.ashbyhq.com/posting-api/job-board"

_EMPLOYMENT_MAP = {
    "FullTime":   "full_time",
    "PartTime":   "part_time",
    "Contract":   "contract",
    "Internship": "contract",
    "Temporary":  "contract",
}


def _strip_html(raw: str) -> str:
    """Convert Ashby HTML job description to readable plain text."""
    # Preserve newlines at block boundaries before stripping tags
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"</(p|li|div|h[1-6]|tr)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    # Collapse 3+ blank lines → 2
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _employment_type(ashby_type: str | None) -> str | None:
    return _EMPLOYMENT_MAP.get(ashby_type or "")


async def fetch_ashby_postings(board_identifier: str) -> list[dict[str, Any]]:
    """
    Call the Ashby public Posting API and return the list of job postings.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            ASHBY_POSTING_API,
            json={"boardIdentifier": board_identifier},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data, dict):
        return data.get("results", []) or data.get("jobs", []) or []
    if isinstance(data, list):
        return data
    return []


async def sync_company_from_ashby(company_id: int) -> dict[str, Any]:
    """
    Full sync for one company:
      1. Fetch all active postings from Ashby
      2. Upsert each posting as a Job row
      3. Mark jobs no longer on Ashby as filled
      4. Stamp company.ashby_last_synced_at

    Returns {"created": N, "updated": N, "expired": N, "errors": N}
    """
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Company, Job, JobStatus
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as db:
        company: Company | None = (
            await db.execute(select(Company).where(Company.id == company_id))
        ).scalar_one_or_none()

        if not company:
            raise ValueError(f"Company {company_id} not found")
        if not company.ashby_identifier:
            raise ValueError(f"Company {company_id} has no ashby_identifier set")

        log.info(
            "ashby-sync: company=%d (%s) identifier=%s",
            company_id, company.name, company.ashby_identifier,
        )

        try:
            postings = await fetch_ashby_postings(company.ashby_identifier)
        except httpx.HTTPStatusError as exc:
            log.error("ashby-sync: HTTP %s for company %d", exc.response.status_code, company_id)
            raise
        except Exception as exc:
            log.error("ashby-sync: fetch failed for company %d: %s", company_id, exc)
            raise

        log.info("ashby-sync: fetched %d postings for company %d", len(postings), company_id)

        seen_external_ids: set[str] = set()
        created = updated = expired = errors = 0

        for posting in postings:
            # Skip unlisted / draft postings
            if not posting.get("isListed", True):
                continue

            ashby_id = posting.get("id") or posting.get("jobId") or ""
            if not ashby_id:
                continue

            external_id = f"ashby:{ashby_id}"
            seen_external_ids.add(external_id)

            # Parse fields — Ashby field names vary slightly across API versions
            title    = posting.get("title") or posting.get("jobTitle") or "Untitled Role"
            location = (
                posting.get("locationName")
                or posting.get("location")
                or (posting.get("locations") or [{}])[0].get("locationName")
            )
            emp_type = _employment_type(
                posting.get("employmentType") or posting.get("type")
            )
            jd_html  = posting.get("descriptionHtml") or posting.get("description") or ""
            full_jd  = _strip_html(jd_html) if jd_html else posting.get("descriptionPlain", "")
            # First 400 chars as summary fallback
            summary  = (full_jd[:400].rsplit(" ", 1)[0] + "…") if len(full_jd) > 400 else full_jd or None

            try:
                existing: Job | None = (
                    await db.execute(select(Job).where(Job.external_id == external_id))
                ).scalar_one_or_none()

                if existing:
                    existing.title      = title
                    existing.location   = location
                    existing.employment = emp_type
                    existing.full_jd    = full_jd or existing.full_jd
                    existing.summary    = summary or existing.summary
                    existing.status     = JobStatus.active
                    updated += 1
                else:
                    import secrets
                    job = Job(
                        external_id=external_id,
                        company_id=company_id,
                        company=company.name,
                        title=title,
                        location=location,
                        employment=emp_type,
                        stage=company.stage,
                        sector=company.sector,
                        full_jd=full_jd,
                        summary=summary,
                        founder_name=company.founder_name,
                        founder_email=company.founder_email,
                        founder_wa=company.founder_wa,
                        founder_access_token=secrets.token_urlsafe(32),
                        stack=[],
                        signals=[],
                        status=JobStatus.active,
                    )
                    db.add(job)
                    created += 1

            except Exception as exc:
                log.error("ashby-sync: error processing posting %s: %s", external_id, exc)
                errors += 1

        # Expire jobs from this company that are no longer on Ashby
        all_ashby_jobs: list[Job] = (
            await db.execute(
                select(Job).where(
                    Job.company_id == company_id,
                    Job.external_id.like("ashby:%"),
                    Job.status == JobStatus.active,
                )
            )
        ).scalars().all()

        for job in all_ashby_jobs:
            if job.external_id not in seen_external_ids:
                job.status = JobStatus.filled
                expired += 1
                log.info("ashby-sync: expired job %s (%s)", job.external_id, job.title)

        company.ashby_last_synced_at = datetime.now(timezone.utc)
        await db.commit()

    log.info(
        "ashby-sync done: company=%d created=%d updated=%d expired=%d errors=%d",
        company_id, created, updated, expired, errors,
    )
    return {"created": created, "updated": updated, "expired": expired, "errors": errors}


async def sync_all_companies() -> dict[str, Any]:
    """Sync every company that has an ashby_identifier. Called by the daily scheduler."""
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Company
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as db:
        companies: list[Company] = (
            await db.execute(
                select(Company).where(Company.ashby_identifier.isnot(None))
            )
        ).scalars().all()

    results: dict[str, Any] = {}
    for company in companies:
        try:
            results[company.name] = await sync_company_from_ashby(company.id)
        except Exception as exc:
            results[company.name] = {"error": str(exc)}

    return results
