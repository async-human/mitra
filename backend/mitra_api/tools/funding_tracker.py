"""
mitra_api/tools/funding_tracker.py

Funding discovery + ATS probing for Indian startups.

  1. Scan Inc42 / StartupTalky for Series A/B tech raises
  2. Probe Greenhouse → Ashby → Lever slug patterns
  3. Upsert companies and sync jobs when ATS is found
  4. Queue no-ATS companies for manual founder outreach
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

# Known Indian startups — explicit ATS slugs where auto-discovery fails
BOOTSTRAP_COMPANIES: list[dict[str, str]] = [
    {"name": "Setu", "stage": "Series B", "sector": "Fintech"},
    {"name": "Pronto", "stage": "Series A", "sector": "Mobility", "greenhouse_slug": "pronto"},
    {"name": "Hyperface", "stage": "Series A", "sector": "Fintech"},
    {"name": "Slice", "stage": "Series B", "sector": "Fintech", "greenhouse_slug": "slice"},
    {"name": "Jar", "stage": "Series B", "sector": "Consumer"},
    {"name": "Khatabook", "stage": "Series C", "sector": "B2B SaaS"},
    {
        "name": "Razorpay",
        "stage": "Series D",
        "sector": "Fintech",
        "greenhouse_slug": "razorpaysoftwareprivatelimited",
    },
    {"name": "CRED", "stage": "Series D", "sector": "Fintech", "lever_slug": "cred"},
    {"name": "Groww", "stage": "Series D", "sector": "Fintech", "greenhouse_slug": "groww"},
    {"name": "Zepto", "stage": "Series E", "sector": "Consumer"},
    {"name": "Postman", "stage": "Series D", "sector": "Developer Tools", "greenhouse_slug": "postman"},
    {"name": "PhonePe", "stage": "Series D", "sector": "Fintech", "greenhouse_slug": "phonepe"},
    {"name": "Meesho", "stage": "Series F", "sector": "Consumer", "lever_slug": "meesho"},
    {"name": "BrowserStack", "stage": "Series B", "sector": "Developer Tools"},
    {"name": "Chargebee", "stage": "Series H", "sector": "B2B SaaS"},
]


def _generate_slugs(company_name: str) -> list[str]:
    raw = company_name.lower().strip()
    raw = re.sub(r"\b(pvt|ltd|private|limited|inc|technologies|tech|labs|ai|hq)\b", "", raw)
    raw = re.sub(r"[^a-z0-9\s]", "", raw)
    raw = re.sub(r"\s+", "-", raw).strip("-")
    base = raw.replace("-", "")

    candidates = [raw, base, f"{raw}-hq", f"get{base}", f"{base}-india", f"{base}hq", raw.replace("-", "")]
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
            if resp.status_code == 200:
                return len(resp.json().get("jobs", [])) > 0
    except Exception:
        pass
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
            if resp.status_code == 200:
                data = resp.json()
                return isinstance(data, list) and len(data) > 0
    except Exception:
        pass
    return False


async def discover_ats(company_name: str) -> dict[str, Any] | None:
    for slug in _generate_slugs(company_name):
        if await _probe_greenhouse(slug):
            return {
                "ats": "greenhouse",
                "slug": slug,
                "board_url": f"https://boards.greenhouse.io/{slug}",
            }
        if await _probe_ashby(slug):
            return {
                "ats": "ashby",
                "slug": slug,
                "board_url": f"https://jobs.ashbyhq.com/{slug}",
            }
        if await _probe_lever(slug):
            return {
                "ats": "lever",
                "slug": slug,
                "board_url": f"https://jobs.lever.co/{slug}",
            }
    return None


_FUNDING_SYSTEM_PROMPT = """You extract Indian startup funding announcements from article text.

For each funding announcement, return:
  company_name, amount_usd, stage (pre_seed|seed|series_a|series_b|series_c|series_d|unknown),
  sector, location, is_tech (bool), investors (max 3)

Only include is_tech=true and stage series_a or series_b.
Return ONLY a JSON array."""


async def extract_funding_from_text(article_text: str, api_key: str) -> list[dict[str, Any]]:
    if not api_key.strip():
        log.warning("funding extraction skipped — no ANTHROPIC_API_KEY")
        return []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1024,
                    "temperature": 0.0,
                    "system": _FUNDING_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": article_text[:4000]}],
                },
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
            raw = resp.json()["content"][0]["text"].strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            result = json.loads(raw)
            return result if isinstance(result, list) else []
    except Exception:
        log.exception("funding extraction failed")
        return []


async def _scrape_funding_page(url: str, api_key: str) -> list[dict[str, Any]]:
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
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return await extract_funding_from_text(text[:5000], api_key)
    except Exception:
        log.exception("funding page scrape failed: %s", url)
        return []


def _normalise_stage(raw: str) -> str:
    mapping = {
        "pre_seed": "Pre-Seed",
        "seed": "Seed",
        "series_a": "Series A",
        "series_b": "Series B",
        "series_c": "Series C",
        "series_d": "Series D",
    }
    return mapping.get(raw.lower().replace(" ", "_"), raw)


async def _sync_company_jobs(company_id: int, ats: str) -> int:
    if ats == "greenhouse":
        from mitra_api.tools.greenhouse import sync_company_from_greenhouse
        result = await sync_company_from_greenhouse(company_id)
        return int(result.get("created", 0))
    if ats == "ashby":
        from mitra_api.tools.ashby import sync_company_from_ashby
        result = await sync_company_from_ashby(company_id)
        return int(result.get("created", 0))
    if ats == "lever":
        from mitra_api.tools.lever import sync_company_from_lever
        result = await sync_company_from_lever(company_id)
        return int(result.get("created", 0))
    return 0


def _known_ats_info(entry: dict[str, str]) -> dict[str, Any] | None:
    if entry.get("greenhouse_slug"):
        slug = entry["greenhouse_slug"]
        return {
            "ats": "greenhouse",
            "slug": slug,
            "board_url": f"https://boards.greenhouse.io/{slug}",
        }
    if entry.get("lever_slug"):
        slug = entry["lever_slug"]
        return {
            "ats": "lever",
            "slug": slug,
            "board_url": f"https://jobs.lever.co/{slug}",
        }
    if entry.get("ashby_identifier"):
        slug = entry["ashby_identifier"]
        return {
            "ats": "ashby",
            "slug": slug,
            "board_url": f"https://jobs.ashbyhq.com/{slug}",
        }
    return None


async def _upsert_company_with_ats(
    db,
    *,
    company_name: str,
    ats_info: dict[str, Any],
    stage: str | None,
    sector: str | None,
    location: str | None,
    extra_signals: dict[str, Any] | None = None,
) -> tuple[Any, bool]:
    """Returns (company, created)."""
    from mitra_api.db.models import Company
    from sqlalchemy import select

    existing = (
        await db.execute(
            select(Company).where(Company.name.ilike(company_name))
        )
    ).scalar_one_or_none()

    signals = {
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        **(extra_signals or {}),
    }

    if existing:
        company = existing
        created = False
        if ats_info["ats"] == "greenhouse" and not company.greenhouse_slug:
            company.greenhouse_slug = ats_info["slug"]
        elif ats_info["ats"] == "ashby" and not company.ashby_identifier:
            company.ashby_identifier = ats_info["slug"]
        elif ats_info["ats"] == "lever" and not company.lever_slug:
            company.lever_slug = ats_info["slug"]
        company.board_url = company.board_url or ats_info.get("board_url")
        company.source = company.source or "funding_tracker"
        company.signals = {**(company.signals or {}), **signals}
    else:
        kwargs: dict[str, Any] = {
            "name": company_name,
            "stage": stage,
            "sector": sector,
            "location": location or "India",
            "source": "funding_tracker",
            "board_url": ats_info.get("board_url"),
            "signals": signals,
            "founder_access_token": secrets.token_urlsafe(32),
        }
        if ats_info["ats"] == "greenhouse":
            kwargs["greenhouse_slug"] = ats_info["slug"]
        elif ats_info["ats"] == "ashby":
            kwargs["ashby_identifier"] = ats_info["slug"]
        elif ats_info["ats"] == "lever":
            kwargs["lever_slug"] = ats_info["slug"]
        company = Company(**kwargs)
        db.add(company)
        created = True

    await db.flush()
    return company, created


async def bootstrap_known_startups(db, *, dry_run: bool = False) -> dict[str, Any]:
    """Discover ATS + sync jobs for curated Indian startup list."""
    stats = {"processed": 0, "ats_found": 0, "jobs_synced": 0, "skipped": 0, "errors": 0}

    for entry in BOOTSTRAP_COMPANIES:
        name = entry["name"]
        stats["processed"] += 1

        ats_info = _known_ats_info(entry) or await discover_ats(name)

        if not ats_info:
            log.info("bootstrap: no ATS for %s", name)
            stats["skipped"] += 1
            continue

        stats["ats_found"] += 1
        if dry_run:
            log.info("DRY RUN bootstrap: %s → %s", name, ats_info)
            continue

        try:
            company, _ = await _upsert_company_with_ats(
                db,
                company_name=name,
                ats_info=ats_info,
                stage=entry.get("stage"),
                sector=entry.get("sector"),
                location=entry.get("location", "India"),
                extra_signals={"bootstrap": True},
            )
            await db.commit()
            synced = await _sync_company_jobs(company.id, ats_info["ats"])
            stats["jobs_synced"] += synced
        except Exception:
            log.exception("bootstrap failed for %s", name)
            stats["errors"] += 1

    if not dry_run:
        await db.commit()
    return stats


async def run_funding_discovery_pipeline(
    db,
    api_key: str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    from mitra_api.db.models import Company
    from sqlalchemy import select

    stats = {
        "funding_events_found": 0,
        "new_companies": 0,
        "ats_found": 0,
        "queued_for_outreach": 0,
        "jobs_synced": 0,
    }

    all_events: list[dict] = []
    all_events.extend(await _scrape_funding_page("https://inc42.com/buzz/funding/", api_key))
    all_events.extend(
        await _scrape_funding_page(
            "https://startuptalky.com/indian-startups-funding-investors-data-2026/",
            api_key,
        )
    )

    seen: set[str] = set()
    unique_events = []
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

        existing = (
            await db.execute(select(Company).where(Company.name.ilike(company_name)))
        ).scalar_one_or_none()
        if existing:
            continue

        stats["new_companies"] += 1
        if dry_run:
            continue

        ats_info = await discover_ats(company_name)
        stage = _normalise_stage(event.get("stage", ""))
        sector = event.get("sector")
        location = event.get("location", "India")
        funding_signals = {
            "amount_usd": event.get("amount_usd"),
            "investors": event.get("investors", []),
        }

        if ats_info:
            stats["ats_found"] += 1
            company, _ = await _upsert_company_with_ats(
                db,
                company_name=company_name,
                ats_info=ats_info,
                stage=stage,
                sector=sector,
                location=location,
                extra_signals=funding_signals,
            )
            await db.commit()
            stats["jobs_synced"] += await _sync_company_jobs(company.id, ats_info["ats"])
        else:
            stats["queued_for_outreach"] += 1
            company = Company(
                name=company_name,
                stage=stage,
                sector=sector,
                location=location,
                source="funding_tracker",
                signals={
                    **funding_signals,
                    "needs_outreach": True,
                    "outreach_reason": "no_ats_found",
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                },
                founder_access_token=secrets.token_urlsafe(32),
            )
            db.add(company)

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
            "id": c.id,
            "name": c.name,
            "stage": c.stage,
            "sector": c.sector,
            "location": c.location,
            "signals": c.signals,
        }
        for c in companies
    ]
