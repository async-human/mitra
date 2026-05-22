"""
mitra_api/tools/funding_tracker.py

Funding discovery + ATS probing for Indian startups.

  1. Scrape Inc42 / StartupTalky / VCCircle for recent raises
  2. LLM-extract structured funding events (provider-agnostic via get_llm_adapter)
  3. Probe Greenhouse → Ashby → Lever slug patterns for each new company
  4. Upsert companies + sync jobs when ATS is found
  5. Queue no-ATS companies for manual founder outreach

Provider switching is env-only:
  MITRA_LLM_PROVIDER=openai   MITRA_LLM_CHEAP_MODEL=gpt-4o-mini        (default)
  MITRA_LLM_PROVIDER=anthropic MITRA_LLM_CHEAP_MODEL=claude-haiku-4-5-20251001
"""

from __future__ import annotations

import json
import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Any

import httpx

log = logging.getLogger(__name__)

# ── Scraping sources ──────────────────────────────────────────────────────────
# Each URL is scraped for funding news; the LLM extracts structured events.
# Add or swap URLs here — no code changes needed elsewhere.
_FUNDING_SOURCES: list[str] = [
    "https://inc42.com/buzz/funding/",
    "https://startuptalky.com/indian-startups-funding-investors-data-2026/",
    "https://www.vccircle.com/deals/funding",
]

# ── LLM extraction ────────────────────────────────────────────────────────────

_FUNDING_SYSTEM_PROMPT = """\
You extract Indian startup funding announcements from article text.

For each funding round found, return a JSON object with these fields:
  company_name  (string)
  amount_usd    (integer, USD — null if unknown)
  stage         (one of: pre_seed | seed | series_a | series_b | series_c | series_d | series_e | series_f | growth | ipo | unknown)
  sector        (string, e.g. "Fintech", "B2B SaaS", "Consumer", "Developer Tools")
  location      (string, default "India")
  is_tech       (boolean)
  investors     (array of strings, max 3 names)
  founder_name  (string or null — include only if explicitly mentioned in the article)

Only include is_tech=true companies. Skip non-tech, real estate, pharma.
Return ONLY a valid JSON array — no markdown, no explanation.\
"""


async def extract_funding_from_text(article_text: str) -> list[dict[str, Any]]:
    """Use the configured LLM (cheap model) to extract funding events from scraped text."""
    from mitra_api.config import get_settings
    from mitra_api.llm.factory import get_llm_adapter
    from mitra_api.llm.types import ChatMessage

    s = get_settings()
    adapter = get_llm_adapter(s)
    try:
        result = await adapter.complete(
            model=s.mitra_llm_cheap_model,
            messages=[
                ChatMessage(role="system", content=_FUNDING_SYSTEM_PROMPT),
                ChatMessage(role="user",   content=article_text[:5000]),
            ],
            tools=None,
            max_tokens=1500,
            temperature=0.0,
        )
        raw = (result.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        log.exception("funding extraction failed")
        return []


# ── ATS probing ───────────────────────────────────────────────────────────────

def _generate_slugs(company_name: str) -> list[str]:
    raw = company_name.lower().strip()
    raw = re.sub(r"\b(pvt|ltd|private|limited|inc|technologies|tech|labs|ai|hq)\b", "", raw)
    raw = re.sub(r"[^a-z0-9\s]", "", raw)
    raw = re.sub(r"\s+", "-", raw).strip("-")
    base = raw.replace("-", "")
    candidates = [raw, base, f"{raw}-hq", f"get{base}", f"{base}-india", f"{base}hq"]
    seen: set[str] = set()
    result: list[str] = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            result.append(c)
    return result[:6]


async def _probe_greenhouse(slug: str) -> bool:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            return resp.status_code == 200 and len(resp.json().get("jobs", [])) > 0
    except Exception:
        return False


async def _probe_ashby(slug: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "https://api.ashbyhq.com/posting-api/job-board",
                json={"boardIdentifier": slug},
            )
            if resp.status_code == 200:
                data = resp.json()
                postings = data.get("jobPostings") or data.get("results") or []
                return len(postings) > 0
    except Exception:
        pass
    return False


async def _probe_lever(slug: str) -> bool:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            return resp.status_code == 200 and isinstance(resp.json(), list) and len(resp.json()) > 0
    except Exception:
        return False


async def discover_ats(company_name: str) -> dict[str, Any] | None:
    for slug in _generate_slugs(company_name):
        if await _probe_greenhouse(slug):
            return {"ats": "greenhouse", "slug": slug, "board_url": f"https://boards.greenhouse.io/{slug}"}
        if await _probe_ashby(slug):
            return {"ats": "ashby",      "slug": slug, "board_url": f"https://jobs.ashbyhq.com/{slug}"}
        if await _probe_lever(slug):
            return {"ats": "lever",      "slug": slug, "board_url": f"https://jobs.lever.co/{slug}"}
    return None


# ── DB helpers ────────────────────────────────────────────────────────────────

def _normalise_stage(raw: str) -> str:
    mapping = {
        "pre_seed": "Pre-Seed", "seed": "Seed",
        "series_a": "Series A", "series_b": "Series B",
        "series_c": "Series C", "series_d": "Series D",
        "series_e": "Series E", "series_f": "Series F",
        "growth": "Growth",     "ipo": "IPO",
    }
    return mapping.get(raw.lower().replace(" ", "_").replace("-", "_"), raw)


async def _sync_company_jobs(company_id: int, ats: str) -> int:
    if ats == "greenhouse":
        from mitra_api.tools.greenhouse import sync_company_from_greenhouse
        return int((await sync_company_from_greenhouse(company_id)).get("created", 0))
    if ats == "ashby":
        from mitra_api.tools.ashby import sync_company_from_ashby
        return int((await sync_company_from_ashby(company_id)).get("created", 0))
    if ats == "lever":
        from mitra_api.tools.lever import sync_company_from_lever
        return int((await sync_company_from_lever(company_id)).get("created", 0))
    return 0


async def _upsert_company(
    db, *, company_name: str, stage: str | None, sector: str | None,
    location: str | None, founder_name: str | None,
    ats_info: dict[str, Any] | None, extra_signals: dict[str, Any] | None,
) -> tuple[Any, bool]:
    from mitra_api.db.models import Company
    from sqlalchemy import select

    existing = (
        await db.execute(select(Company).where(Company.name.ilike(company_name)))
    ).scalar_one_or_none()

    signals = {"discovered_at": datetime.now(timezone.utc).isoformat(), **(extra_signals or {})}

    if existing:
        company = existing
        if ats_info:
            if ats_info["ats"] == "greenhouse" and not company.greenhouse_slug:
                company.greenhouse_slug = ats_info["slug"]
            elif ats_info["ats"] == "ashby" and not company.ashby_identifier:
                company.ashby_identifier = ats_info["slug"]
            elif ats_info["ats"] == "lever" and not company.lever_slug:
                company.lever_slug = ats_info["slug"]
            company.board_url = company.board_url or ats_info.get("board_url")
        company.source  = company.source  or "funding_tracker"
        company.signals = {**(company.signals or {}), **signals}
        if founder_name and not company.founder_name:
            company.founder_name = founder_name
        return company, False

    kwargs: dict[str, Any] = {
        "name": company_name, "stage": stage, "sector": sector,
        "location": location or "India", "source": "funding_tracker",
        "signals": signals, "founder_access_token": secrets.token_urlsafe(32),
    }
    if founder_name:
        kwargs["founder_name"] = founder_name
    if ats_info:
        kwargs["board_url"] = ats_info.get("board_url")
        if ats_info["ats"] == "greenhouse": kwargs["greenhouse_slug"]  = ats_info["slug"]
        elif ats_info["ats"] == "ashby":    kwargs["ashby_identifier"] = ats_info["slug"]
        elif ats_info["ats"] == "lever":    kwargs["lever_slug"]       = ats_info["slug"]
    company = Company(**kwargs)
    db.add(company)
    return company, True


# ── Scraping ──────────────────────────────────────────────────────────────────

async def _scrape_page(url: str) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MitraBot/1.0)"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            text = resp.text
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>",  "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return await extract_funding_from_text(text)
    except Exception:
        log.exception("funding page scrape failed: %s", url)
        return []


# ── Public API ────────────────────────────────────────────────────────────────

async def run_funding_discovery_pipeline(db, *, dry_run: bool = False) -> dict[str, Any]:
    """
    Scrape funding news sources, extract events via LLM, upsert companies,
    probe ATS, and sync jobs.  Provider/model controlled entirely by env vars.
    """
    from mitra_api.db.models import Company
    from sqlalchemy import select

    stats = {
        "sources_scraped": len(_FUNDING_SOURCES),
        "funding_events_found": 0,
        "new_companies": 0,
        "updated_companies": 0,
        "ats_found": 0,
        "queued_for_outreach": 0,
        "jobs_synced": 0,
    }

    all_events: list[dict] = []
    for url in _FUNDING_SOURCES:
        events = await _scrape_page(url)
        log.info("funding scrape: %s → %d events", url, len(events))
        all_events.extend(events)

    # Deduplicate by company name
    seen: set[str] = set()
    unique_events: list[dict] = []
    for e in all_events:
        name = (e.get("company_name") or "").lower().strip()
        if name and name not in seen:
            seen.add(name)
            unique_events.append(e)

    stats["funding_events_found"] = len(unique_events)

    for event in unique_events:
        company_name = (event.get("company_name") or "").strip()
        if not company_name:
            continue

        stage      = _normalise_stage(event.get("stage", ""))
        sector     = event.get("sector")
        location   = event.get("location", "India")
        founder    = event.get("founder_name") or None
        funding_signals = {
            "amount_usd": event.get("amount_usd"),
            "investors":  event.get("investors") or [],
        }

        if dry_run:
            log.info("DRY RUN: %s  stage=%s  amount=%s", company_name, stage, funding_signals.get("amount_usd"))
            stats["new_companies"] += 1
            continue

        ats_info = await discover_ats(company_name)
        company, created = await _upsert_company(
            db,
            company_name=company_name,
            stage=stage,
            sector=sector,
            location=location,
            founder_name=founder,
            ats_info=ats_info,
            extra_signals=funding_signals,
        )
        await db.flush()

        if created:
            stats["new_companies"] += 1
        else:
            stats["updated_companies"] += 1

        if ats_info:
            stats["ats_found"] += 1
            synced = await _sync_company_jobs(company.id, ats_info["ats"])
            stats["jobs_synced"] += synced
        else:
            stats["queued_for_outreach"] += 1
            if not (company.signals or {}).get("needs_outreach"):
                company.signals = {
                    **(company.signals or {}),
                    "needs_outreach": True,
                    "outreach_reason": "no_ats_found",
                }

    if not dry_run:
        await db.commit()

    return stats


async def get_outreach_queue(db) -> list[dict[str, Any]]:
    from mitra_api.db.models import Company
    from sqlalchemy import select

    companies = (
        await db.execute(
            select(Company)
            .where(Company.signals.contains({"needs_outreach": True}))
            .order_by(Company.created_at.desc())
            .limit(50)
        )
    ).scalars().all()

    return [
        {
            "id": c.id, "name": c.name, "stage": c.stage,
            "sector": c.sector, "location": c.location,
            "signals": c.signals,
        }
        for c in companies
    ]
