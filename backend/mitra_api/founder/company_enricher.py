"""
mitra_api/founder/company_enricher.py

Enriches a job posting with structured company metadata using the LLM.

Runs as a fire-and-forget background task after job creation.
Stores results in Job.signals under the "company_info" key.
"""

from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)

_ENRICH_SYSTEM = """You are a company research assistant with broad knowledge of startups and technology companies worldwide.

Given a company name and optional context, return structured company metadata as a JSON object.
Return ONLY valid JSON — no markdown fences, no explanation, nothing else.
Omit any key you are not confident about. Never invent or hallucinate data.

JSON schema (use exactly these key names):
{
  "website_url":    "full URL including https, e.g. https://tredence.com — omit if unsure",
  "linkedin_url":   "LinkedIn company page URL, e.g. https://linkedin.com/company/tredence — construct from company slug if the pattern is clear",
  "founded_year":   integer year e.g. 2013 — omit if unknown,
  "employee_range": "one of: 1-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5001-10000, 10000+",
  "funding_stage":  "Bootstrapped | Pre-seed | Seed | Series A | Series B | Series C | Series D+ | Public | PE-backed | Private",
  "total_funding":  "human-readable string e.g. '$116M' or '₹450 Cr' — omit if unknown",
  "hq_location":    "city and country e.g. 'Bengaluru, India' — omit if unknown",
  "investors":      ["up to 5 notable investor or parent company names — omit array if unknown"],
  "description":    "1-2 sentence company description focused on what they build and who they serve"
}

Priority order — most important fields first: website_url, linkedin_url, description, employee_range, founded_year.
For linkedin_url the slug pattern is usually the company name in lowercase with hyphens replacing spaces."""


async def enrich_company(
    *,
    company_name: str,
    sector: str | None = None,
    location: str | None = None,
    job_id: int,
) -> None:
    """
    Fire-and-forget: enriches Job.signals["company_info"] for the given job.
    Silently logs errors — never raises so it cannot break the job creation flow.
    """
    import asyncio
    from mitra_api.config import get_settings
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job as JobModel
    from mitra_api.llm.factory import get_llm_adapter
    from mitra_api.llm.types import ChatMessage
    from sqlalchemy import select

    if not company_name or not company_name.strip():
        return

    s = get_settings()

    context_parts = [f"Company name: {company_name.strip()}"]
    if sector:
        context_parts.append(f"Sector / industry: {sector}")
    if location:
        context_parts.append(f"Known location: {location}")

    user_content = "\n".join(context_parts)

    # Small delay so the job commit is visible before we read it back
    await asyncio.sleep(0.5)

    try:
        adapter = get_llm_adapter(s)
        result = await adapter.complete(
            model=s.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_ENRICH_SYSTEM),
                ChatMessage(role="user",   content=user_content),
            ],
            tools=None,
            max_tokens=512,
            temperature=0.0,
        )
    except Exception:
        log.exception("company_enricher: LLM call failed for company=%r job_id=%d", company_name, job_id)
        return

    raw = (result.content or "").strip()
    # Strip markdown fences if the model wrapped the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
        if "```" in raw:
            raw = raw[:raw.index("```")]

    try:
        info: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("company_enricher: non-JSON response for company=%r: %s", company_name, raw[:200])
        return

    if not isinstance(info, dict) or not info:
        return

    # Normalise investors to a list of strings
    if "investors" in info and not isinstance(info["investors"], list):
        del info["investors"]

    # Persist into Job.signals["company_info"]
    factory = get_session_factory()
    try:
        async with factory() as db:
            job = (await db.execute(
                select(JobModel).where(JobModel.id == job_id)
            )).scalar_one_or_none()
            if job is None:
                log.warning("company_enricher: job_id=%d not found", job_id)
                return
            sigs: dict = dict(job.signals) if isinstance(job.signals, dict) else {}
            sigs["company_info"] = info
            job.signals = sigs
            await db.commit()
            log.info(
                "company_enricher: stored company_info for job_id=%d company=%r keys=%s",
                job_id, company_name, list(info.keys()),
            )
    except Exception:
        log.exception("company_enricher: DB write failed for job_id=%d", job_id)
