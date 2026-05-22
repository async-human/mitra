"""
mitra_api/tools/website_resolver.py

Reliable website URL resolution for Indian startups.

Four-layer pipeline (tried in order, first hit wins):

  Layer 1 — ATS board URL (zero cost, already in DB)
             Greenhouse/Ashby boards return company website as a structured field.

  Layer 2 — Crunchbase public autocomplete (no API key, excellent coverage)
             Virtually every funded Indian startup is on Crunchbase.

  Layer 3 — Tavily web search (requires TAVILY_API_KEY)
             Searches for company official website, filters aggregators.

  Layer 4 — Domain inference + HTTP verification
             Tries common patterns: companyname.com/.in/.co/.io
             Only stores if the server actually responds 200.

Every URL returned is verified — HEAD-requested before being stored.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus, urlparse

import httpx

log = logging.getLogger(__name__)

_AGGREGATOR_DOMAINS = {
    "linkedin.com", "crunchbase.com", "tracxn.com", "inc42.com",
    "yourstory.com", "entrackr.com", "techcrunch.com", "moneycontrol.com",
    "economictimes.com", "livemint.com", "business-standard.com",
    "wellfound.com", "angellist.com", "glassdoor.com", "indeed.com",
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "wikipedia.org", "bloomberg.com", "reuters.com", "forbes.com",
    "startuptalky.com", "thecareerlabs.com",
}

_VERIFY_TIMEOUT = 5.0
_SEARCH_TIMEOUT = 10.0


# ── URL helpers ───────────────────────────────────────────────────────────────

async def _verify_url(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    try:
        async with httpx.AsyncClient(
            timeout=_VERIFY_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MitraBot/1.0)"},
        ) as client:
            resp = await client.head(url)
            return resp.status_code < 400
    except Exception:
        return False


def _is_aggregator(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return any(host == d or host.endswith("." + d) for d in _AGGREGATOR_DOMAINS)
    except Exception:
        return False


def _normalise_url(raw: str) -> str | None:
    if not raw:
        return None
    raw = raw.strip().rstrip("/")
    if not raw.startswith("http"):
        raw = "https://" + raw
    return raw if re.match(r"https?://[^\s/$.?#].[^\s]*", raw) else None


# ── Layer 1: ATS board ────────────────────────────────────────────────────────

async def _resolve_from_ats_board(
    greenhouse_slug: str | None = None,
    ashby_slug: str | None = None,
) -> str | None:
    if greenhouse_slug:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://boards-api.greenhouse.io/v1/boards/{greenhouse_slug}"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    website = (
                        data.get("company", {}).get("website") or
                        data.get("organization", {}).get("website")
                    )
                    if website:
                        url = _normalise_url(website)
                        if url and not _is_aggregator(url) and await _verify_url(url):
                            log.info("website_resolver: Greenhouse → %s", url)
                            return url
        except Exception:
            pass

    if ashby_slug:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.ashbyhq.com/posting-api/job-board",
                    json={"boardIdentifier": ashby_slug},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    website = (
                        data.get("organization", {}).get("websiteUrl") or
                        data.get("jobBoard", {}).get("websiteUrl")
                    )
                    if website:
                        url = _normalise_url(website)
                        if url and not _is_aggregator(url) and await _verify_url(url):
                            log.info("website_resolver: Ashby → %s", url)
                            return url
        except Exception:
            pass

    return None


# ── Layer 2: Crunchbase ───────────────────────────────────────────────────────

async def _resolve_from_crunchbase(company_name: str) -> str | None:
    try:
        async with httpx.AsyncClient(
            timeout=_SEARCH_TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; MitraBot/1.0)",
                "Accept": "application/json",
            },
        ) as client:
            resp = await client.get(
                "https://autocomplete.crunchbase.com/v4/data/autocomplete",
                params={
                    "query":          company_name,
                    "collection_ids": "organizations",
                    "limit":          5,
                },
            )
            if resp.status_code != 200:
                return None

            for entity in resp.json().get("entities", []):
                props = entity.get("properties", {})
                name  = props.get("name", "").lower()
                if company_name.lower() not in name and name not in company_name.lower():
                    continue

                permalink = props.get("permalink", "")
                if not permalink:
                    continue

                org_resp = await client.get(
                    f"https://www.crunchbase.com/organization/{permalink}",
                    follow_redirects=True,
                )
                if org_resp.status_code == 200:
                    match = re.search(r'"homepage_url"\s*:\s*"([^"]+)"', org_resp.text)
                    if match:
                        url = _normalise_url(match.group(1))
                        if url and not _is_aggregator(url) and await _verify_url(url):
                            log.info("website_resolver: Crunchbase → %s", url)
                            return url
    except Exception:
        log.debug("website_resolver: crunchbase failed for %s", company_name)

    return None


# ── Layer 3: Tavily search ────────────────────────────────────────────────────

async def _resolve_from_search(company_name: str, sector: str | None = None) -> str | None:
    try:
        from mitra_api.config import get_settings
        s = get_settings()
        if not s.tavily_api_key:
            return None

        sector_hint = f" {sector}" if sector else ""
        query = f'"{company_name}"{sector_hint} India startup official website'

        async with httpx.AsyncClient(timeout=_SEARCH_TIMEOUT) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key":        s.tavily_api_key,
                    "query":          query,
                    "search_depth":   "basic",
                    "max_results":    5,
                    "include_answer": False,
                },
            )
            if resp.status_code != 200:
                return None

            name_slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
            for r in resp.json().get("results", []):
                url = _normalise_url(r.get("url", ""))
                if not url or _is_aggregator(url):
                    continue
                title = r.get("title", "").lower()
                if name_slug in url.lower() or company_name.lower() in title:
                    if await _verify_url(url):
                        parsed = urlparse(url)
                        root = f"{parsed.scheme}://{parsed.netloc}"
                        if await _verify_url(root):
                            log.info("website_resolver: Tavily → %s", root)
                            return root
    except Exception:
        log.debug("website_resolver: tavily failed for %s", company_name)

    return None


# ── Layer 4: Domain inference ─────────────────────────────────────────────────

async def _resolve_from_domain_inference(company_name: str) -> str | None:
    clean = re.sub(
        r"\b(pvt|ltd|private|limited|inc|technologies|tech|labs|ai|hq|india)\b",
        "", company_name.lower().strip()
    )
    slug = re.sub(r"[^a-z0-9]", "", clean)
    slug_hyphen = re.sub(r"\s+", "-", re.sub(r"[^a-z0-9\s]", "", clean).strip())

    candidates = [
        f"https://{slug}.com",
        f"https://{slug}.in",
        f"https://{slug}.co",
        f"https://{slug}.io",
        f"https://www.{slug}.com",
        f"https://www.{slug}.in",
        f"https://get{slug}.com",
        f"https://{slug_hyphen}.com",
        f"https://{slug_hyphen}.in",
        f"https://{slug}.ai",
        f"https://{slug}.co.in",
    ]

    for url in candidates:
        if await _verify_url(url):
            log.info("website_resolver: domain inference → %s", url)
            return url

    return None


# ── Public API ────────────────────────────────────────────────────────────────

async def resolve_company_website(
    company_name: str,
    *,
    sector: str | None = None,
    greenhouse_slug: str | None = None,
    ashby_slug: str | None = None,
    existing_website: str | None = None,
) -> str | None:
    """
    Resolve the official website URL for a company.
    Tries four layers in order, returns first verified URL.
    Every URL returned has been HEAD-verified — no hallucinated domains.
    """
    if not company_name:
        return None

    if existing_website:
        url = _normalise_url(existing_website)
        if url and await _verify_url(url):
            return url
        log.info("website_resolver: existing URL dead for %s: %s", company_name, existing_website)

    log.info("website_resolver: resolving '%s'", company_name)

    if greenhouse_slug or ashby_slug:
        url = await _resolve_from_ats_board(greenhouse_slug, ashby_slug)
        if url:
            return url

    url = await _resolve_from_crunchbase(company_name)
    if url:
        return url

    url = await _resolve_from_search(company_name, sector)
    if url:
        return url

    url = await _resolve_from_domain_inference(company_name)
    if url:
        return url

    log.info("website_resolver: could not resolve '%s'", company_name)
    return None


# ── Backfill for FundedStartup rows missing websites ─────────────────────────

async def backfill_funded_startup_websites(db) -> dict[str, int]:
    """
    Resolve and save website URLs for all FundedStartup rows where website IS NULL.
    """
    from mitra_api.db.models import FundedStartup
    from sqlalchemy import select

    rows = (await db.execute(
        select(FundedStartup).where(FundedStartup.website.is_(None))
    )).scalars().all()

    log.info("website backfill: %d funded_startups missing website", len(rows))
    resolved = failed = 0

    for row in rows:
        url = await resolve_company_website(row.name, sector=row.sector)
        if url:
            row.website = url
            resolved += 1
            log.info("backfill: %s → %s", row.name, url)
        else:
            failed += 1

    await db.commit()
    log.info("website backfill done: resolved=%d failed=%d", resolved, failed)
    return {"resolved": resolved, "failed": failed}
