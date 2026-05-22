"""
mitra_api/tools/funding_tracker.py

Two parallel systems for Indian startup intelligence:

  RSS Funding Feed (FundedStartup table — external only, source='rss')
    1. Fetch RSS feeds from Indian startup news sources
    2. LLM-extract structured funding events
    3. Upsert into funded_startups — powers the public /startups page
    Never reads from or writes to the operational Company table.

  ATS Bootstrap (Company table — separate, operational)
    1. Probe Greenhouse → Ashby → Lever for curated startups
    2. Upsert operational Company rows + sync India engineering jobs
    3. Queue no-ATS companies for manual outreach via get_outreach_queue()

Provider switching is env-only — no code changes needed:
  MITRA_LLM_PROVIDER=openai    MITRA_LLM_CHEAP_MODEL=gpt-4o-mini
  MITRA_LLM_PROVIDER=anthropic MITRA_LLM_CHEAP_MODEL=claude-haiku-4-5-20251001
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

log = logging.getLogger(__name__)

# ── RSS feed sources ──────────────────────────────────────────────────────────
# All are RSS/Atom — no JS challenge, no Cloudflare, bot-friendly.
# Google News RSS is the most reliable: aggregates all major Indian publications.
_RSS_FEEDS: list[str] = [
    "https://news.google.com/rss/search?q=India+startup+funding+Series&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Indian+startup+seed+funding+raised&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Indian+startup+Series+C+D+funding&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Indian+startup+raised+crore+million&hl=en-IN&gl=IN&ceid=IN:en",
    "https://inc42.com/feed/",
    "https://techcrunch.com/tag/india/feed/",
    "https://yourstory.com/feed",
]

_LLM_BATCH_SIZE = 35

# Only one RSS+LLM pipeline at a time (startup seed, /public/companies, scheduler share this).
_pipeline_lock = asyncio.Lock()
_last_pipeline_stats: dict[str, Any] | None = None

_FUNDING_HEADLINE_KEYWORDS = (
    "funding", "raises", "raised", " crore", "million", " billion",
    "series a", "series b", "series c", "series d", "series e", "series f",
    "seed round", "pre-seed", "secures", "bags ", "closes ", "investment",
)

_ROUNDUP_HEADLINE_PHRASES = (
    "funding and acquisitions", "this week", "startups from", "startups raised",
    "weekly roundup", "acquisitions in", "between ", "including ",
)


@dataclass
class RssItem:
    title: str
    description: str
    link: str | None = None
    pub_date: datetime | None = None

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MitraFundingBot/1.0; +https://mitra.work)"}

# Atom namespace
_ATOM_NS = "http://www.w3.org/2005/Atom"

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


# ── RSS parsing ───────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_pub_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _parse_feed(xml_text: str) -> list[RssItem]:
    """Parse RSS 2.0 or Atom feed into structured items."""
    items: list[RssItem] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    for item in root.findall(".//item"):
        title = _strip_html(item.findtext("title") or "")
        desc  = _strip_html(item.findtext("description") or "")
        link  = (item.findtext("link") or "").strip() or None
        pub   = _parse_pub_date(item.findtext("pubDate"))
        if title:
            items.append(RssItem(title=title, description=desc[:300], link=link, pub_date=pub))

    for entry in root.findall(f".//{{{_ATOM_NS}}}entry"):
        title   = _strip_html(entry.findtext(f"{{{_ATOM_NS}}}title")   or "")
        summary = _strip_html(entry.findtext(f"{{{_ATOM_NS}}}summary") or "")
        link_el = entry.find(f"{{{_ATOM_NS}}}link")
        link    = link_el.get("href") if link_el is not None else None
        pub_raw = entry.findtext(f"{{{_ATOM_NS}}}published") or entry.findtext(f"{{{_ATOM_NS}}}updated")
        pub     = _parse_pub_date(pub_raw)
        if title:
            items.append(RssItem(title=title, description=summary[:300], link=link, pub_date=pub))

    return items


async def _fetch_rss(url: str) -> list[RssItem]:
    """Fetch one RSS feed and return parsed items."""
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
You extract Indian tech startup funding announcements from numbered news headlines.

For each genuine Indian tech startup funding round, return a JSON object with:
  headline_index  (integer — the headline number this event came from)
  company_name    (string — brand name ONLY, 1–4 words, e.g. "Razorpay", "Anscer Robotics", "Oolka". Never a headline fragment, never "Indian Fintech Startup X", never a weekly roundup title)
  amount_usd      (integer in USD — null if not mentioned or unclear)
  stage           (one of: pre_seed | seed | series_a | series_b | series_c | series_d | series_e | series_f | growth | ipo | bridge | unknown)
  sector          (string — e.g. "Fintech", "B2B SaaS", "Consumer", "Developer Tools", "AI / SaaS", "Healthtech")
  location        (string — city or "India")
  investors       (array of strings, up to 5 investor names — empty array if none mentioned)
  founder_name    (string or null — CEO/co-founder name from headline or description, e.g. "founded by X", "CEO X")
  website         (string or null — official company website with https://, e.g. https://razorpay.com — only if confident)
  funded_at       (string "YYYY-MM-DD" or null — best estimate of announcement date from headline context)

Conversion: ₹1 crore ≈ $120,000. ₹1000 crore ≈ $120M.

Rules:
- Include ALL stages from pre-seed through growth/IPO — do not filter to only Series A/B
- Only Indian tech startups (software, fintech, SaaS, consumer-tech, health-tech, etc.)
- Skip: real estate, pharma, manufacturing, pure M&A, secondary sales
- Extract as many distinct companies as the headlines support — aim for breadth, not just the largest rounds
- One entry per company (dedupe within your response)
- headline_index must match the numbered headline the event came from
- headline_index MUST point to the headline that specifically describes THIS company's funding round — never assign an unrelated index

Return ONLY a valid JSON array — no markdown, no commentary.\
"""


def _dedupe_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for event in events:
        name = _sanitize_company_name((event.get("company_name") or "").strip()) or ""
        if not name:
            continue
        event = {**event, "company_name": name}
        key = name.lower()
        prev = by_name.get(key)
        if not prev:
            by_name[key] = event
            continue
        prev_amt = prev.get("amount_usd") or 0
        new_amt = event.get("amount_usd") or 0
        if new_amt >= prev_amt:
            by_name[key] = event
    return list(by_name.values())


def _parse_funded_at(raw: str | None, fallback: datetime | None = None) -> datetime | None:
    if raw:
        try:
            dt = datetime.fromisoformat(raw[:10])
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return fallback


def _company_tokens(name: str) -> list[str]:
    stop = {"pvt", "ltd", "private", "limited", "inc", "labs", "the", "and", "for"}
    tokens: list[str] = []
    for part in re.split(r"[\W_]+", name.lower()):
        if len(part) >= 3 and part not in stop:
            tokens.append(part)
    return tokens


def _headline_mentions_company(company_name: str, item: RssItem) -> bool:
    hay = f"{item.title} {item.description}".lower()
    name_lower = company_name.lower()
    if name_lower in hay:
        return True
    tokens = _company_tokens(company_name)
    long_hits = sum(1 for t in tokens if len(t) >= 4 and t in hay)
    if long_hits >= 1:
        return True
    if len(tokens) >= 2 and sum(1 for t in tokens if t in hay) >= 2:
        return True
    return False


def _mention_score(company_name: str, item: RssItem) -> int:
    hay = f"{item.title} {item.description}".lower()
    score = 0
    if company_name.lower() in hay:
        score += 10
    for token in _company_tokens(company_name):
        if token in hay:
            score += 4 if len(token) >= 4 else 1
    if _is_funding_headline(item.title):
        score += 2
    return score


def _find_best_source_item(
    company_name: str,
    all_items: list[RssItem],
    preferred_idx: int | None,
) -> RssItem | None:
    """Resolve the RSS item that actually mentions this company's funding."""
    if preferred_idx is not None and 0 <= preferred_idx < len(all_items):
        candidate = all_items[preferred_idx]
        if _headline_mentions_company(company_name, candidate):
            return candidate

    best: RssItem | None = None
    best_score = 0
    for item in all_items:
        if _is_roundup_headline(item.title):
            continue
        if not _headline_mentions_company(company_name, item):
            continue
        score = _mention_score(company_name, item)
        if score > best_score:
            best_score = score
            best = item
    return best if best_score >= 3 else None


async def _extract_batch(
    adapter, model: str, items: list[RssItem], *, global_offset: int = 0,
) -> list[dict[str, Any]]:
    from mitra_api.llm.types import ChatMessage

    numbered = "\n".join(
        f"{global_offset + i + 1}. {it.title}. {it.description[:180]}"
        for i, it in enumerate(items)
    )
    result = await adapter.complete(
        model=model,
        messages=[
            ChatMessage(role="system", content=_EXTRACTION_SYSTEM),
            ChatMessage(role="user",   content=f"Headlines:\n{numbered}"),
        ],
        tools=None,
        max_tokens=4096,
        temperature=0.0,
    )
    raw = (result.content or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, list) else []


async def extract_funding_from_headlines(items: list[RssItem]) -> list[dict[str, Any]]:
    """Extract funding events from RSS items — batched LLM calls for full coverage."""
    if not items:
        return []

    from mitra_api.config import get_settings
    from mitra_api.llm.factory import get_llm_adapter

    candidates: list[tuple[int, RssItem]] = [
        (i, item) for i, item in enumerate(items)
        if _is_funding_headline(item.title) and not _is_roundup_headline(item.title)
    ]
    if not candidates:
        return []

    log.info(
        "funding LLM: pre-filtered %d/%d headlines for extraction",
        len(candidates), len(items),
    )

    s       = get_settings()
    adapter = get_llm_adapter(s)
    all_events: list[dict[str, Any]] = []
    llm_failed = False

    for batch_start in range(0, len(candidates), _LLM_BATCH_SIZE):
        batch_slice = candidates[batch_start:batch_start + _LLM_BATCH_SIZE]
        batch_items = [item for _, item in batch_slice]
        global_offset = batch_slice[0][0]
        try:
            batch_events = await _extract_batch(
                adapter, s.mitra_llm_cheap_model, batch_items, global_offset=global_offset,
            )
            all_events.extend(batch_events)
            log.info(
                "funding LLM batch %d–%d (of %d candidates): extracted %d events",
                batch_start + 1, batch_start + len(batch_slice), len(candidates), len(batch_events),
            )
        except Exception:
            llm_failed = True
            log.exception("funding LLM batch failed at candidate offset %d", batch_start)
            break

    if llm_failed and not all_events:
        return []

    return _dedupe_events(all_events)


def _is_funding_headline(title: str) -> bool:
    lower = title.lower()
    return any(kw in lower for kw in _FUNDING_HEADLINE_KEYWORDS)


def _is_roundup_headline(title: str) -> bool:
    lower = title.lower()
    return any(p in lower for p in _ROUNDUP_HEADLINE_PHRASES)


_BAD_NAME_PHRASES = (
    "funding and acquisitions", "this week", "startups from", "startups raised",
    "weekly roundup", "funding alert", "acquisitions in", "startup ecosystem",
    "between ", "including ", "diverse sectors", " as many as ",
    "inference problem", "problem,", "entertainment sector",
)

_JUNK_PREFIX = re.compile(
    r"^[\{\[\(]?\s*(?:funding\s*alert[\}\]\)]?\s*)?",
    re.I,
)

_STARTUP_NAME = re.compile(
    r"(?:indian(?:\s+\w+){0,8}\s+)?(?:\w+\s+){0,5}startup\s+"
    r"((?:[A-Za-z][\w.\-&']*(?:\s+(?!raises\b|raised\b|bags\b|secures\b|closes\b|gets\b)"
    r"[A-Za-z][\w.\-&']*){0,3}))"
    r"(?:\s+(?:raises|raised|bags|secures|closes|gets|\$)|$)",
    re.I,
)

_DESCRIPTOR_PREFIX = re.compile(
    r"^(?:indian(?:\s+\w+){0,8}\s+)?(?:\w+\s+){0,5}startup\s+",
    re.I,
)


def _is_plausible_company_name(name: str) -> bool:
    if not name or len(name) < 2 or len(name) > 45:
        return False
    lower = name.lower().strip()
    if any(p in lower for p in _BAD_NAME_PHRASES):
        return False
    if re.search(r"[\{\[\(]", name):
        return False
    words = name.split()
    if len(words) > 5:
        return False
    if lower.startswith(("funding", "weekly", "top ", "indian ", "india's ", "ai ")):
        return False
    descriptive = {
        "indian", "india", "startup", "startups", "funding", "wearable", "fintech",
        "automation", "industrial", "entertainment", "sector", "problem", "inference",
    }
    if sum(1 for w in words if w.lower() in descriptive) >= 2 and len(words) > 2:
        return False
    return True


def _sanitize_company_name(raw: str) -> str | None:
    name = _JUNK_PREFIX.sub("", raw.strip().strip('"\'')).strip()
    name = re.split(r"\[|\(", name)[0].strip()
    if " - " in name:
        name = name.split(" - ", 1)[0].strip()

    m = _STARTUP_NAME.search(name)
    if m:
        name = m.group(1).strip()
    else:
        name = _DESCRIPTOR_PREFIX.sub("", name).strip()

    name = re.sub(r"\s+", " ", name).strip(" ,.-")
    name = re.sub(
        r"\s+(?:raises|raised|bags|secures|closes|gets)(?:\s+\$.*)?$",
        "",
        name,
        flags=re.I,
    ).strip()
    if not _is_plausible_company_name(name):
        return None
    return name


def _guess_company_name(title: str) -> str:
    title = title.strip()
    m = _STARTUP_NAME.search(title)
    if m:
        return m.group(1).strip()

    for sep in (" raises ", " Raises ", " bags ", " Bags ", " secures ", " closes ", " gets ", " Raises $", " raises $"):
        idx = title.find(sep)
        if idx > 0:
            candidate = _sanitize_company_name(title[:idx])
            if candidate:
                return candidate

    if " - " in title:
        candidate = _sanitize_company_name(title.split(" - ", 1)[0])
        if candidate:
            return candidate

    candidate = _sanitize_company_name(title[:80])
    return candidate or title[:80].strip()


def _parse_amount_from_title(title: str) -> int | None:
    m = re.search(r"\$\s*([\d,.]+)\s*(b|billion|m|million|k)?", title, re.I)
    if m and m.group(1):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            val = 0
        if val <= 0:
            return None
        unit = (m.group(2) or "m").lower()
        if unit in ("b", "billion"):
            return int(val * 1_000_000_000)
        if unit in ("m", "million"):
            return int(val * 1_000_000)
        if unit == "k":
            return int(val * 1_000)
        return int(val * 1_000_000) if val < 1000 else int(val)
    lower = title.lower()
    m = re.search(r"(?:rs\.?|₹)\s*([\d,.]+)\s*(crore|cr|lakh)?", lower)
    if m and m.group(1):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            return None
        unit = (m.group(2) or "crore").lower()
        if unit in ("crore", "cr"):
            return int(val * 120_000)
        if unit == "lakh":
            return int(val * 1_200)
    return None


def _heuristic_extract_from_rss(items: list[RssItem]) -> list[dict[str, Any]]:
    """Fallback when LLM is unavailable — parse funding signals from RSS titles directly."""
    keywords = (
        "funding", "raises", "raised", " crore", "million", " billion",
        "series a", "series b", "series c", "series d", "series e",
        "seed round", "pre-seed", "secures", "bags ", "closes ",
    )
    stage_patterns = [
        (re.compile(r"pre[- ]?seed", re.I), "pre_seed"),
        (re.compile(r"\bseed\b", re.I), "seed"),
        (re.compile(r"series f", re.I), "series_f"),
        (re.compile(r"series e", re.I), "series_e"),
        (re.compile(r"series d", re.I), "series_d"),
        (re.compile(r"series c", re.I), "series_c"),
        (re.compile(r"series b", re.I), "series_b"),
        (re.compile(r"series a", re.I), "series_a"),
    ]
    events: list[dict[str, Any]] = []
    for i, item in enumerate(items):
        title = item.title.strip()
        lower = title.lower()
        if not any(kw in lower for kw in keywords):
            continue
        name = _sanitize_company_name(_guess_company_name(title))
        if not name:
            continue
        if any(bad in lower for bad in _BAD_NAME_PHRASES):
            continue
        stage = "unknown"
        for pat, st in stage_patterns:
            if pat.search(lower):
                stage = st
                break
        events.append({
            "headline_index": i + 1,
            "company_name": name,
            "amount_usd": _parse_amount_from_title(title),
            "stage": stage,
            "sector": None,
            "location": "India",
            "investors": [],
            "founder_name": None,
            "website": None,
            "funded_at": item.pub_date.strftime("%Y-%m-%d") if item.pub_date else None,
        })
    return _dedupe_events(events)


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


def _known_ats_info(entry: dict[str, str]) -> dict[str, Any] | None:
    if entry.get("greenhouse_slug"):
        slug = entry["greenhouse_slug"]
        return {"ats": "greenhouse", "slug": slug, "board_url": f"https://boards.greenhouse.io/{slug}"}
    if entry.get("lever_slug"):
        slug = entry["lever_slug"]
        return {"ats": "lever", "slug": slug, "board_url": f"https://jobs.lever.co/{slug}"}
    if entry.get("ashby_identifier"):
        slug = entry["ashby_identifier"]
        return {"ats": "ashby", "slug": slug, "board_url": f"https://jobs.ashbyhq.com/{slug}"}
    return None


async def _upsert_company_with_ats(
    db, *, company_name: str, ats_info: dict[str, Any],
    stage: str | None, sector: str | None, location: str | None,
    extra_signals: dict[str, Any] | None = None,
) -> tuple[Any, bool]:
    """Upsert an operational Company row with ATS identifiers."""
    from mitra_api.db.models import Company
    from sqlalchemy import select

    existing = (
        await db.execute(select(Company).where(Company.name.ilike(company_name)))
    ).scalar_one_or_none()

    signals = {"discovered_at": datetime.now(timezone.utc).isoformat(), **(extra_signals or {})}

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
        company.source = company.source or "bootstrap"
        company.signals = {**(company.signals or {}), **signals}
    else:
        kwargs: dict[str, Any] = {
            "name": company_name, "stage": stage, "sector": sector,
            "location": location or "India", "source": "bootstrap",
            "board_url": ats_info.get("board_url"), "signals": signals,
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


async def _queue_for_outreach(
    db, *, company_name: str, stage: str | None, sector: str | None,
    location: str | None, reason: str,
) -> None:
    """Add a no-ATS company to the operational outreach queue."""
    from mitra_api.db.models import Company
    from sqlalchemy import select

    existing = (
        await db.execute(select(Company).where(Company.name.ilike(company_name)))
    ).scalar_one_or_none()

    signals = {
        "needs_outreach": True,
        "outreach_reason": reason,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }

    if existing:
        existing.signals = {**(existing.signals or {}), **signals}
        existing.source = existing.source or "bootstrap"
        return

    db.add(Company(
        name=company_name, stage=stage, sector=sector,
        location=location or "India", source="bootstrap", signals=signals,
        founder_access_token=secrets.token_urlsafe(32),
    ))


async def bootstrap_known_startups(db, *, dry_run: bool = False) -> dict[str, Any]:
    """Discover ATS + sync jobs for curated Indian startup list."""
    stats: dict[str, Any] = {
        "processed": 0, "ats_found": 0, "jobs_synced": 0,
        "skipped": 0, "queued_for_outreach": 0, "errors": 0,
    }

    for entry in BOOTSTRAP_COMPANIES:
        name = entry["name"]
        stats["processed"] += 1
        ats_info = _known_ats_info(entry) or await discover_ats(name)

        if not ats_info:
            log.info("bootstrap: no ATS for %s", name)
            stats["skipped"] += 1
            if not dry_run:
                await _queue_for_outreach(
                    db,
                    company_name=name,
                    stage=entry.get("stage"),
                    sector=entry.get("sector"),
                    location=entry.get("location", "India"),
                    reason="no_ats_found",
                )
                stats["queued_for_outreach"] += 1
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
            stats["jobs_synced"] += await _sync_company_jobs(company.id, ats_info["ats"])
        except Exception:
            log.exception("bootstrap failed for %s", name)
            stats["errors"] += 1

    if not dry_run:
        await db.commit()
    return stats


async def _upsert_funded_startup(
    db, *, company_name: str, stage: str | None, sector: str | None,
    location: str | None, founder_name: str | None,
    amount_usd: int | None, investors: list[str],
    board_url: str | None,
    website: str | None = None,
    source_url: str | None = None,
    funded_at: datetime | None = None,
) -> tuple[Any, bool]:
    from mitra_api.db.models import FundedStartup
    from sqlalchemy import select

    company_name = company_name.strip()[:200]
    if source_url:
        source_url = source_url[:480]
    if website:
        website = _normalize_website(website)
    if amount_usd is not None and amount_usd > 10_000_000_000:
        amount_usd = None

    existing = (
        await db.execute(select(FundedStartup).where(FundedStartup.name.ilike(company_name)))
    ).scalar_one_or_none()

    if existing:
        if amount_usd and (not existing.amount_usd or amount_usd > existing.amount_usd):
            existing.amount_usd = amount_usd
        if investors and (not existing.investors or len(investors) > len(existing.investors or [])):
            existing.investors = investors
        if founder_name and not existing.founder_name:
            existing.founder_name = founder_name
        if board_url and not existing.board_url:
            existing.board_url = board_url
        if stage and (not existing.stage or existing.stage.lower() == "unknown"):
            existing.stage = stage
        if sector and not existing.sector:
            existing.sector = sector
        if location and not existing.location:
            existing.location = location
        if website and not existing.website:
            existing.website = website
        if source_url:
            existing.source_url = source_url
        if funded_at and not existing.funded_at:
            existing.funded_at = funded_at
        existing.source = "rss"
        return existing, False

    startup = FundedStartup(
        name=company_name,
        stage=stage,
        sector=sector,
        location=location or "India",
        founder_name=founder_name,
        amount_usd=amount_usd,
        investors=investors or [],
        board_url=board_url,
        website=website,
        source_url=source_url,
        funded_at=funded_at,
        source="rss",
    )
    db.add(startup)
    return startup, True


def _normalize_website(raw: str | None) -> str | None:
    if not raw:
        return None
    url = raw.strip()
    if not url or url.lower() in ("null", "none", "n/a"):
        return None
    if not url.startswith(("http://", "https://")):
        url = f"https://{url.lstrip('/')}"
    return url[:280]


def _normalize_founder_name(raw: str | None) -> str | None:
    if not raw:
        return None
    name = str(raw).strip()
    if not name or name.lower() in ("null", "none", "n/a", "unknown"):
        return None
    if len(name) < 3 or len(name) > 80 or len(name.split()) > 5:
        return None
    return name[:200]


_ENRICH_STARTUP_SYSTEM = """\
You enrich Indian startup metadata. Given a numbered list of startups, return a JSON array.
Each object must include:
  company_name  (string — exact name from the list)
  founder_name  (string or null — CEO or co-founder full name, only if well-known or clearly inferrable)
  website       (string or null — official company website with https://, only if confident)

Rules:
- Only include facts you are highly confident about — never invent founders or URLs
- For website, prefer the company's own domain (not LinkedIn, Crunchbase, or news articles)
- Return one object per startup in the list (use null for unknown fields)
- Return ONLY valid JSON — no markdown\
"""


async def _llm_enrich_startups_batch(rows: list[Any]) -> dict[str, dict[str, str | None]]:
    from mitra_api.config import get_settings
    from mitra_api.llm.factory import get_llm_adapter
    from mitra_api.llm.types import ChatMessage

    if not rows:
        return {}

    s = get_settings()
    adapter = get_llm_adapter(s)
    numbered = "\n".join(
        f"{i + 1}. {row.name} — {row.sector or 'sector unknown'}, {row.location or 'India'}"
        for i, row in enumerate(rows)
    )
    try:
        result = await adapter.complete(
            model=s.mitra_llm_cheap_model,
            messages=[
                ChatMessage(role="system", content=_ENRICH_STARTUP_SYSTEM),
                ChatMessage(role="user", content=f"Startups:\n{numbered}"),
            ],
            tools=None,
            max_tokens=2048,
            temperature=0.0,
        )
    except Exception:
        log.exception("startup enrichment LLM batch failed")
        return {}

    raw = (result.content or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("startup enrichment: non-JSON response: %s", raw[:200])
        return {}

    if not isinstance(parsed, list):
        return {}

    out: dict[str, dict[str, str | None]] = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = (item.get("company_name") or "").strip()
        if not name:
            continue
        out[name.lower()] = {
            "founder_name": (item.get("founder_name") or None),
            "website": _normalize_website(item.get("website")),
        }
    return out


async def _tavily_enrich_one(name: str, sector: str | None) -> dict[str, str | None]:
    from mitra_api.config import get_settings
    from mitra_api.tools.market_research import web_market_research

    s = get_settings()
    if not (s.tavily_api_key or "").strip():
        return {}

    sector_bit = f" {sector}" if sector else ""
    query = f'"{name}"{sector_bit} India startup founder CEO official website'
    search = await web_market_research(query, s)
    if not search.get("ok"):
        return {}

    from mitra_api.llm.factory import get_llm_adapter
    from mitra_api.llm.types import ChatMessage

    adapter = get_llm_adapter(s)
    try:
        result = await adapter.complete(
            model=s.mitra_llm_cheap_model,
            messages=[
                ChatMessage(
                    role="system",
                    content=(
                        "Extract startup metadata from web search results. "
                        'Return JSON: {"founder_name": string|null, "website": string|null}. '
                        "Only confident facts. Website must be the company's own domain."
                    ),
                ),
                ChatMessage(
                    role="user",
                    content=f"Startup: {name}\n\nSearch results:\n{search.get('message', '')[:3000]}",
                ),
            ],
            tools=None,
            max_tokens=256,
            temperature=0.0,
        )
    except Exception:
        log.exception("startup tavily parse failed for %s", name)
        return {}

    raw = (result.content or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    if not isinstance(data, dict):
        return {}
    return {
        "founder_name": (data.get("founder_name") or None),
        "website": _normalize_website(data.get("website")),
    }


async def enrich_funded_startups_metadata(db) -> dict[str, int]:
    """Fill missing founder_name / website for RSS startups via LLM (+ optional Tavily)."""
    from mitra_api.db.models import FundedStartup
    from sqlalchemy import or_, select

    rows = list((
        await db.execute(
            select(FundedStartup)
            .where(FundedStartup.source == "rss")
            .where(or_(FundedStartup.founder_name.is_(None), FundedStartup.website.is_(None)))
            .order_by(FundedStartup.updated_at.desc())
            .limit(40)
        )
    ).scalars().all())

    stats = {"candidates": len(rows), "founders_added": 0, "websites_added": 0, "tavily_enriched": 0}
    if not rows:
        return stats

    for batch_start in range(0, len(rows), 12):
        batch = rows[batch_start:batch_start + 12]
        enriched = await _llm_enrich_startups_batch(batch)
        for row in batch:
            data = enriched.get(row.name.lower(), {})
            if data.get("founder_name") and not row.founder_name:
                founder = _normalize_founder_name(data["founder_name"])
                if founder:
                    row.founder_name = founder
                    stats["founders_added"] += 1
            if data.get("website") and not row.website:
                row.website = data["website"]
                stats["websites_added"] += 1

    still_missing = [
        r for r in rows
        if not r.founder_name or not r.website
    ][:8]
    for row in still_missing:
        extra = await _tavily_enrich_one(row.name, row.sector)
        if not extra:
            continue
        stats["tavily_enriched"] += 1
        if extra.get("founder_name") and not row.founder_name:
            founder = _normalize_founder_name(extra["founder_name"])
            if founder:
                row.founder_name = founder
                stats["founders_added"] += 1
        if extra.get("website") and not row.website:
            row.website = extra["website"]
            stats["websites_added"] += 1

    await db.flush()
    log.info("startup enrichment: %s", stats)
    return stats


async def _relink_funded_startup_sources(db, all_items: list[RssItem]) -> dict[str, int]:
    """Fix or clear source_url for rows whose article does not mention the company."""
    from mitra_api.db.models import FundedStartup
    from sqlalchemy import select

    rows = (
        await db.execute(select(FundedStartup).where(FundedStartup.source == "rss"))
    ).scalars().all()
    stats = {"checked": len(rows), "fixed": 0, "cleared": 0}

    for row in rows:
        preferred_idx: int | None = None
        if row.source_url:
            for i, item in enumerate(all_items):
                if item.link and item.link.split("?")[0] == row.source_url.split("?")[0]:
                    preferred_idx = i
                    break
            if preferred_idx is not None:
                item = all_items[preferred_idx]
                if _headline_mentions_company(row.name, item):
                    continue

        match = _find_best_source_item(row.name, all_items, preferred_idx)
        if match and match.link:
            if row.source_url != match.link:
                row.source_url = match.link[:480]
                stats["fixed"] += 1
        elif row.source_url:
            row.source_url = None
            stats["cleared"] += 1

    if stats["fixed"] or stats["cleared"]:
        await db.flush()
    log.info("source relink: %s", stats)
    return stats


async def _prune_junk_funded_startups(db) -> int:
    """Remove or rename RSS feed rows whose names are headline fragments, not brands."""
    from mitra_api.db.models import FundedStartup
    from sqlalchemy import select

    rows = (
        await db.execute(select(FundedStartup).where(FundedStartup.source == "rss"))
    ).scalars().all()
    removed = 0
    for row in rows:
        cleaned = _sanitize_company_name(row.name)
        if cleaned is None:
            await db.delete(row)
            removed += 1
        elif cleaned != row.name:
            row.name = cleaned
    if removed:
        await db.flush()
    return removed


async def run_funding_discovery_pipeline(db, *, dry_run: bool = False) -> dict[str, Any]:
    """Run RSS funding pipeline; concurrent callers wait for the in-progress run."""
    global _last_pipeline_stats

    if _pipeline_lock.locked():
        log.info("funding_discovery: pipeline already in progress — waiting")
        async with _pipeline_lock:
            return dict(_last_pipeline_stats or {"status": "completed_by_other"})

    async with _pipeline_lock:
        stats = await _run_funding_discovery_pipeline_impl(db, dry_run=dry_run)
        _last_pipeline_stats = stats
        log.info(
            "funding_discovery: finished — new=%s updated=%s skipped_sanitize=%s "
            "events=%s headlines=%s junk_removed=%s founders_added=%s websites_added=%s",
            stats.get("new_companies"),
            stats.get("updated_companies"),
            stats.get("skipped_sanitize"),
            stats.get("funding_events_found"),
            stats.get("headlines_collected"),
            stats.get("junk_rows_removed"),
            stats.get("founders_added"),
            stats.get("websites_added"),
        )
        return stats


async def _run_funding_discovery_pipeline_impl(db, *, dry_run: bool = False) -> dict[str, Any]:
    """
    1. Fetch all RSS feeds in parallel
    2. Deduplicate items
    3. Batched LLM extraction (full feed coverage)
    4. Upsert into funded_startups (source='rss') with source URLs + dates
    """
    stats: dict[str, Any] = {
        "feeds_fetched":        len(_RSS_FEEDS),
        "headlines_collected":  0,
        "funding_events_found": 0,
        "new_companies":        0,
        "updated_companies":    0,
        "junk_rows_removed":    0,
        "skipped_sanitize":     0,
        "founders_added":       0,
        "websites_added":       0,
        "sources_matched":      0,
        "sources_unmatched":    0,
    }

    if not dry_run:
        stats["junk_rows_removed"] = await _prune_junk_funded_startups(db)

    feed_results = await asyncio.gather(*[_fetch_rss(url) for url in _RSS_FEEDS])
    all_items: list[RssItem] = []
    seen_titles: set[str] = set()
    for items in feed_results:
        for item in items:
            key = item.title[:80].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                all_items.append(item)

    stats["headlines_collected"] = len(all_items)
    log.info("funding_discovery: %d unique headlines from %d feeds", len(all_items), len(_RSS_FEEDS))

    if all_items:
        events = await extract_funding_from_headlines(all_items)
        if not events:
            events = _heuristic_extract_from_rss(all_items)
            log.warning(
                "funding_discovery: LLM returned 0 — heuristic fallback extracted %d events",
                len(events),
            )
        stats["funding_events_found"] = len(events)
        log.info("funding_discovery: %d funding events to upsert", len(events))

        if dry_run:
            for e in events:
                log.info(
                    "DRY RUN: %s  stage=%s  amount_usd=%s  investors=%s",
                    e.get("company_name"), e.get("stage"),
                    e.get("amount_usd"), e.get("investors"),
                )
        else:
            for event in events:
                company_name = _sanitize_company_name((event.get("company_name") or "").strip())
                if not company_name:
                    stats["skipped_sanitize"] += 1
                    continue

                headline_idx = event.get("headline_index")
                preferred_idx: int | None = None
                if headline_idx is not None:
                    try:
                        preferred_idx = int(headline_idx) - 1
                    except (TypeError, ValueError):
                        preferred_idx = None

                source_item = _find_best_source_item(company_name, all_items, preferred_idx)
                if source_item:
                    stats["sources_matched"] += 1
                else:
                    stats["sources_unmatched"] += 1

                funded_at = _parse_funded_at(
                    event.get("funded_at"),
                    fallback=source_item.pub_date if source_item else None,
                )

                try:
                    async with db.begin_nested():
                        _, created = await _upsert_funded_startup(
                            db,
                            company_name=company_name,
                            stage=_normalise_stage(event.get("stage") or ""),
                            sector=event.get("sector"),
                            location=event.get("location") or "India",
                            founder_name=_normalize_founder_name(event.get("founder_name")),
                            amount_usd=event.get("amount_usd"),
                            investors=event.get("investors") or [],
                            board_url=None,
                            website=_normalize_website(event.get("website")),
                            source_url=(source_item.link if source_item else None),
                            funded_at=funded_at,
                        )
                        await db.flush()
                    if created:
                        stats["new_companies"] += 1
                    else:
                        stats["updated_companies"] += 1
                except Exception:
                    log.warning("funding_discovery: skipped bad row for %r", company_name[:80])

            await db.commit()
            if all_items:
                relink_stats = await _relink_funded_startup_sources(db, all_items)
                stats["sources_fixed"] = relink_stats.get("fixed", 0)
                stats["sources_cleared"] = relink_stats.get("cleared", 0)
                await db.commit()

    if not dry_run:
        enrich_stats = await enrich_funded_startups_metadata(db)
        stats["founders_added"] = enrich_stats.get("founders_added", 0)
        stats["websites_added"] = enrich_stats.get("websites_added", 0)
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
