"""
mitra_api/tools/funding_tracker.py

Funding discovery + ATS probing for Indian startups.

  1. Fetch RSS feeds from Indian startup news sources (no HTML scraping —
     RSS is bot-friendly, free, and not behind Cloudflare)
  2. LLM-extract structured funding events from RSS titles/summaries
     (provider-agnostic via get_llm_adapter + mitra_llm_cheap_model)
  3. Probe Greenhouse → Ashby → Lever for each new company
  4. Upsert companies + sync jobs when ATS is found
  5. Queue no-ATS companies for manual outreach

Provider switching is env-only — no code changes needed:
  MITRA_LLM_PROVIDER=openai    MITRA_LLM_CHEAP_MODEL=gpt-4o-mini
  MITRA_LLM_PROVIDER=anthropic MITRA_LLM_CHEAP_MODEL=claude-haiku-4-5-20251001
"""

from __future__ import annotations

import json
import logging
import re
import secrets
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import httpx

log = logging.getLogger(__name__)

# ── RSS feed sources ──────────────────────────────────────────────────────────
# All are RSS/Atom — no JS challenge, no Cloudflare, bot-friendly.
# Google News RSS is the most reliable: aggregates all major Indian publications.
_RSS_FEEDS: list[str] = [
    # Google News: broad coverage, aggregates Inc42 + YourStory + Entrackr + ET
    "https://news.google.com/rss/search?q=India+startup+funding+Series&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Indian+startup+raised+crore+million&hl=en-IN&gl=IN&ceid=IN:en",
    # Inc42 native RSS
    "https://inc42.com/feed/",
    # Entrackr — best for Series A/B funding news
    "https://entrackr.com/feed/",
    # YourStory
    "https://yourstory.com/feed",
]

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MitraFundingBot/1.0; +https://mitra.work)"}

# Atom namespace
_ATOM_NS = "http://www.w3.org/2005/Atom"


# ── RSS parsing ───────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_feed(xml_text: str) -> list[str]:
    """
    Parse RSS 2.0 or Atom feed.
    Returns a list of "title. description" strings — one per item.
    """
    items: list[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    # RSS 2.0
    for item in root.findall(".//item"):
        title = _strip_html(item.findtext("title") or "")
        desc  = _strip_html(item.findtext("description") or "")
        if title:
            items.append(f"{title}. {desc[:200]}".strip(" ."))

    # Atom
    for entry in root.findall(f".//{{{_ATOM_NS}}}entry"):
        title   = _strip_html(entry.findtext(f"{{{_ATOM_NS}}}title")   or "")
        summary = _strip_html(entry.findtext(f"{{{_ATOM_NS}}}summary") or "")
        if title:
            items.append(f"{title}. {summary[:200]}".strip(" ."))

    return items


async def _fetch_rss(url: str) -> list[str]:
    """Fetch one RSS feed and return parsed item strings."""
    try:
        async with httpx.AsyncClient(timeout=12.0, headers=_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        parsed = _parse_feed(resp.text)
        log.info("RSS fetch: %s → %d items", url, len(parsed))
        return parsed
    except Exception:
        log.warning("RSS fetch failed: %s", url)
        return []


# ── LLM extraction ────────────────────────────────────────────────────────────

_EXTRACTION_SYSTEM = """\
You extract Indian tech startup funding announcements from news headlines.

For each genuine Indian tech startup funding round you find, return a JSON object:
  company_name  (string — the startup name only, not the parent group)
  amount_usd    (integer in USD — null if not mentioned or unclear)
  stage         (one of: pre_seed | seed | series_a | series_b | series_c | series_d | series_e | series_f | growth | ipo | bridge | unknown)
  sector        (string — e.g. "Fintech", "B2B SaaS", "Consumer", "Developer Tools", "AI / SaaS", "Healthtech", "Edtech", "Logistics")
  location      (string — city or "India" if not specified)
  investors     (array of strings, max 3 investor names — empty array if none mentioned)
  founder_name  (string or null — only if explicitly named in the headline)

Conversion: ₹1 crore ≈ $120,000. ₹1000 crore ≈ $120M.

Strict rules:
- Only include is_tech companies (software, fintech, SaaS, consumer-tech, health-tech, etc.)
- Skip: real estate, pharma, manufacturing, government, M&A deals, secondary sales
- Skip companies that are clearly not Indian
- If the same company appears multiple times, include it only once (latest/largest round)
- If you cannot determine the company is Indian tech, skip it

Return ONLY a valid JSON array — no markdown, no explanation, no commentary.\
"""


async def extract_funding_from_headlines(headlines: list[str]) -> list[dict[str, Any]]:
    """
    Call the cheap LLM to extract funding events from a batch of headlines.
    Provider and model are read from settings — env-only switch.
    """
    if not headlines:
        return []

    from mitra_api.config import get_settings
    from mitra_api.llm.factory import get_llm_adapter
    from mitra_api.llm.types import ChatMessage

    s       = get_settings()
    adapter = get_llm_adapter(s)

    # Number the headlines so the LLM can reference them
    numbered = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines[:80]))

    try:
        result = await adapter.complete(
            model=s.mitra_llm_cheap_model,
            messages=[
                ChatMessage(role="system", content=_EXTRACTION_SYSTEM),
                ChatMessage(role="user",   content=f"Headlines:\n{numbered}"),
            ],
            tools=None,
            max_tokens=2000,
            temperature=0.0,
        )
        raw = (result.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        log.exception("funding LLM extraction failed")
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
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
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
                return len(data.get("jobPostings") or data.get("results") or []) > 0
    except Exception:
        pass
    return False


async def _probe_lever(slug: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
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
        "bridge": "Bridge",
    }
    key = raw.lower().replace(" ", "_").replace("-", "_")
    return mapping.get(key, raw)


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
        # Only update ATS slug if not already set
        if ats_info:
            if ats_info["ats"] == "greenhouse" and not company.greenhouse_slug:
                company.greenhouse_slug = ats_info["slug"]
            elif ats_info["ats"] == "ashby" and not company.ashby_identifier:
                company.ashby_identifier = ats_info["slug"]
            elif ats_info["ats"] == "lever" and not company.lever_slug:
                company.lever_slug = ats_info["slug"]
            company.board_url = company.board_url or ats_info.get("board_url")
        # Merge signals — update amount/investors if we now have them
        existing_signals = company.signals or {}
        if extra_signals and extra_signals.get("amount_usd") and not existing_signals.get("amount_usd"):
            existing_signals.update(extra_signals)
            company.signals = existing_signals
        company.source = company.source or "funding_tracker"
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


# ── Public API ────────────────────────────────────────────────────────────────

async def run_funding_discovery_pipeline(db, *, dry_run: bool = False) -> dict[str, Any]:
    """
    1. Fetch all RSS feeds in parallel
    2. Deduplicate headlines
    3. Single LLM call to extract all funding events
    4. For each new company: probe ATS, upsert, sync jobs
    """
    from mitra_api.db.models import Company
    from sqlalchemy import select
    import asyncio

    stats: dict[str, Any] = {
        "feeds_fetched":        len(_RSS_FEEDS),
        "headlines_collected":  0,
        "funding_events_found": 0,
        "new_companies":        0,
        "updated_companies":    0,
        "ats_found":            0,
        "queued_for_outreach":  0,
        "jobs_synced":          0,
    }

    # 1 — Fetch all RSS feeds in parallel
    feed_results = await asyncio.gather(*[_fetch_rss(url) for url in _RSS_FEEDS])
    all_headlines: list[str] = []
    seen_titles: set[str] = set()
    for items in feed_results:
        for item in items:
            key = item[:80].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                all_headlines.append(item)

    stats["headlines_collected"] = len(all_headlines)
    log.info("funding_discovery: %d unique headlines from %d feeds", len(all_headlines), len(_RSS_FEEDS))

    if not all_headlines:
        log.warning("funding_discovery: no headlines collected — all RSS feeds may be down")
        return stats

    # 2 — Single LLM call for all headlines
    events = await extract_funding_from_headlines(all_headlines)
    stats["funding_events_found"] = len(events)
    log.info("funding_discovery: LLM extracted %d funding events", len(events))

    if dry_run:
        for e in events:
            log.info(
                "DRY RUN: %s  stage=%s  amount_usd=%s  investors=%s",
                e.get("company_name"), e.get("stage"),
                e.get("amount_usd"), e.get("investors"),
            )
        return stats

    # 3 — Upsert each event
    for event in events:
        company_name = (event.get("company_name") or "").strip()
        if not company_name:
            continue

        stage    = _normalise_stage(event.get("stage") or "")
        sector   = event.get("sector")
        location = event.get("location") or "India"
        founder  = event.get("founder_name") or None
        funding_signals = {
            "amount_usd": event.get("amount_usd"),
            "investors":  event.get("investors") or [],
        }

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
            stats["jobs_synced"] += await _sync_company_jobs(company.id, ats_info["ats"])
        else:
            stats["queued_for_outreach"] += 1
            existing_sig = company.signals or {}
            if not existing_sig.get("needs_outreach"):
                company.signals = {**existing_sig, "needs_outreach": True, "outreach_reason": "no_ats_found"}

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
