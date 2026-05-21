"""
mitra_api/tools/linkedin_parser.py

Fetches and parses a LinkedIn profile URL into structured candidate signals.

Flow
----
1. Candidate shares their LinkedIn URL in WhatsApp/web chat
2. Orchestrator detects the URL via regex and calls parse_linkedin_profile()
3. If LINKDAPI_API_KEY is configured: LinkdAPI fetches the profile JSON
4. Signals are extracted and mapped to the same schema as resume_parser.py
5. Signals are merged into the candidate session (no re-asking of extracted facts)

Provider
--------
Uses LinkdAPI (linkdapi.com) — the leading Proxycurl replacement after Proxycurl
was shut down following LinkedIn's Jan 2025 lawsuit.
Endpoint: GET https://linkdapi.com/api/v1/profile/full?username=<slug>
Auth:     X-linkdapi-apikey: <key>
Key env:  LINKDAPI_API_KEY  (set in Railway)
Sign up:  https://linkdapi.com

Graceful degradation
--------------------
- No LINKDAPI_API_KEY → returns {} (orchestrator falls back to manual ask)
- Rate limit / error → returns {} with a warning log
- Private/unreachable profile → returns {} with a warning

Signal schema mirrors resume_parser._EXTRACT_SYSTEM so the two sources are
fully interchangeable from the orchestrator's perspective.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

log = logging.getLogger(__name__)

# Regex to extract a LinkedIn profile URL from free text
# Matches: linkedin.com/in/username, www.linkedin.com/in/username,
#          https://linkedin.com/in/username, etc.
_LINKEDIN_URL_RE = re.compile(
    r"https?://(?:www\.)?linkedin\.com/in/[\w\-%.]+/?",
    re.I,
)

# Also matches plain-text variants the user might paste (no protocol)
_LINKEDIN_BARE_RE = re.compile(
    r"(?<!\S)(?:www\.)?linkedin\.com/in/([\w\-%.]+)/?",
    re.I,
)

# LinkdAPI — Proxycurl replacement, accepts LinkedIn username (slug after /in/)
# Docs: https://linkdapi.com/docs
LINKDAPI_ENDPOINT = "https://linkdapi.com/api/v1/profile/full"


def extract_linkedin_url(text: str) -> str | None:
    """
    Return the first LinkedIn profile URL found in arbitrary text, or None.
    Normalises to https://www.linkedin.com/in/<slug> canonical form.
    """
    m = _LINKEDIN_URL_RE.search(text)
    if m:
        raw = m.group(0).rstrip("/")
        return _canonicalise(raw)

    m = _LINKEDIN_BARE_RE.search(text)
    if m:
        return f"https://www.linkedin.com/in/{m.group(1)}"

    return None


def _canonicalise(url: str) -> str:
    """Ensure the URL starts with https://www.linkedin.com/in/..."""
    url = url.lower()
    if not url.startswith("https://"):
        url = "https://" + url.lstrip("http://").lstrip("/")
    if "//linkedin.com" in url:
        url = url.replace("//linkedin.com", "//www.linkedin.com")
    return url


def _extract_username(url: str) -> str | None:
    """Extract the slug (e.g. 'harshal-shinde') from a LinkedIn profile URL."""
    m = re.search(r"linkedin\.com/in/([\w\-%.]+)/?$", url, re.I)
    return m.group(1).lower() if m else None


def _map_linkdapi_to_signals(data: dict[str, Any], url: str) -> dict[str, Any]:
    """
    Map a LinkdAPI profile JSON to the Mitra candidate signal schema.
    Only includes fields with real data; never guesses or fills defaults.

    LinkdAPI actual response shape (confirmed from live API):
      firstName, lastName, headline, summary
      geo: {city, country, full}  — location
      industry: str
      currentPositions: [{companyName, title, description, start:{year,month}, end:{year,month}}]
      fullPositions:    [{companyName, title, description, start:{year,month}, end:{year,month}}]
      educations: [{schoolName, degree, fieldOfStudy, start:{year}, end:{year}}]
      skills: [str] or [{name}]
    """
    signals: dict[str, Any] = {}
    signals["linkedin"] = url

    # ── Basic identity ────────────────────────────────────────────────────────
    first = (data.get("firstName") or "").strip()
    last  = (data.get("lastName")  or "").strip()
    full  = f"{first} {last}".strip() or (data.get("fullName") or "").strip()
    if full:
        signals["candidate_name"] = full

    headline = (data.get("headline") or "").strip()
    if headline:
        signals["current_role"] = headline

    # geo is a dict {city, country, full} in LinkdAPI
    geo = data.get("geo") or {}
    if isinstance(geo, dict):
        location = (geo.get("full") or geo.get("city") or geo.get("country") or "").strip()
    else:
        location = str(geo).strip()
    if location:
        signals["location"] = location

    summary = (data.get("summary") or "").strip()

    # ── Experience ────────────────────────────────────────────────────────────
    # currentPositions = active roles; fullPositions = complete history (includes current)
    current_positions: list[dict] = data.get("currentPositions") or []
    full_positions: list[dict]    = data.get("fullPositions") or data.get("position") or []

    def _exp_months(exp: dict) -> int:
        start = exp.get("start") or {}
        end   = exp.get("end") or {}
        start_y = int(start.get("year") or 0)
        start_m = int(start.get("month") or 1)
        if end and end.get("year"):
            end_y = int(end.get("year") or 0)
            end_m = int(end.get("month") or 1)
        else:
            from datetime import date
            today = date.today()
            end_y, end_m = today.year, today.month
        if not start_y:
            return 0
        return max(0, (end_y - start_y) * 12 + (end_m - start_m))

    seen_companies: set[str] = set()
    current_company = ""
    current_title   = ""
    previous_companies: list[str] = []
    total_months = 0
    tenure_list: list[int] = []

    for exp in current_positions:
        company = (exp.get("companyName") or exp.get("company") or "").strip()
        title   = (exp.get("title") or "").strip()
        if company and not current_company:
            current_company = company
            current_title   = title
            seen_companies.add(company.lower())
        months = _exp_months(exp)
        if months:
            total_months += months
            tenure_list.append(months)

    for exp in full_positions:
        company = (exp.get("companyName") or exp.get("company") or "").strip()
        title   = (exp.get("title") or "").strip()
        if not company:
            continue
        key = company.lower()
        if key in seen_companies:
            continue
        seen_companies.add(key)
        if not current_company:
            current_company = company
            current_title   = title
        else:
            previous_companies.append(company)
        months = _exp_months(exp)
        if months:
            total_months += months
            tenure_list.append(months)

    if current_company:
        signals["current_company"] = current_company
    if current_title:
        signals["current_role"] = current_title
    if previous_companies:
        signals["previous_companies"] = previous_companies[:8]
    if total_months > 0:
        signals["years_experience"] = round(total_months / 12, 1)

    # ── Education ─────────────────────────────────────────────────────────────
    educations: list[dict] = data.get("educations") or data.get("currentEducation") or []
    if educations:
        top    = educations[0]
        school = (top.get("schoolName") or top.get("school") or top.get("university") or "").strip()
        degree = (top.get("degree") or top.get("degree_name") or "").strip()
        field  = (top.get("fieldOfStudy") or top.get("field_of_study") or "").strip()
        parts  = [p for p in [degree, field, school] if p]
        if parts:
            signals["education"] = ", ".join(parts)

    # ── Tech stack — from skills section ──────────────────────────────────────
    skills_raw = data.get("skills") or []
    skill_names: list[str] = []
    for s in skills_raw:
        name = s if isinstance(s, str) else (s.get("name") or s.get("skill") or "")
        name = name.strip()
        if name:
            skill_names.append(name)

    _SOFT = {"communication", "leadership", "teamwork", "management",
             "problem solving", "analytical", "microsoft office", "excel",
             "presentation", "time management", "project management"}
    tech_skills = [s for s in skill_names if s.lower() not in _SOFT]
    if len(tech_skills) >= 2:
        signals["primary_stack"] = tech_skills[:12]
        if len(tech_skills) > 12:
            signals["secondary_stack"] = tech_skills[12:20]

    # ── Behavioral signals ────────────────────────────────────────────────────
    all_exp_list = list(current_positions) + list(full_positions)

    # startup experience: description mentions startup keywords
    has_startup = any(
        any(kw in (exp.get("description") or "").lower()
            for kw in ("startup", "seed", "series a", "series b", "founded by"))
        for exp in all_exp_list
    )
    signals["has_startup_experience"] = has_startup

    # leadership titles
    _LEAD = re.compile(
        r"\b(lead|head|vp|vice president|director|principal|staff|architect|"
        r"co-founder|cofounder|cto|ceo|founder)\b", re.I
    )
    signals["has_leadership_experience"] = any(
        _LEAD.search(exp.get("title") or "") for exp in all_exp_list
    )

    # stability_seeking: median tenure
    if len(tenure_list) >= 2:
        recent = tenure_list[:3]
        median_months = sorted(recent)[len(recent) // 2]
        if median_months >= 36:
            signals["stability_seeking"] = "high"
        elif median_months <= 14:
            signals["stability_seeking"] = "low"

    # first_startup_move
    _ENTERPRISE = re.compile(
        r"\b(tcs|infosys|wipro|accenture|cognizant|ibm|capgemini|hcl|"
        r"google|amazon|microsoft|meta|apple|netflix|salesforce|oracle|"
        r"sap|deloitte|pwc|ey|kpmg)\b", re.I
    )
    all_companies = ([current_company] + previous_companies) if current_company else previous_companies
    if all_companies and not has_startup:
        non_empty = [c for c in all_companies if c]
        if non_empty and sum(1 for c in non_empty if _ENTERPRISE.search(c)) == len(non_empty):
            signals["first_startup_move"] = True

    # ownership_mindset & builder_vs_maintainer — text signals
    all_text = " ".join(
        (exp.get("title") or "") + " " + (exp.get("description") or "")
        for exp in all_exp_list
    ) + " " + summary

    _OWNERSHIP_HIGH = re.compile(
        r"\b(co-?founder|founding engineer|first engineer|"
        r"built from scratch|0.?to.?1|sole developer|solo)\b", re.I
    )
    if _OWNERSHIP_HIGH.search(all_text):
        signals["ownership_mindset"] = "high"
    elif len(all_exp_list) >= 2:
        all_titles = " ".join(exp.get("title") or "" for exp in all_exp_list)
        if not re.search(r"\b(lead|architect|principal|staff|head|director|founder)\b", all_titles, re.I):
            signals["ownership_mindset"] = "low"

    _BUILDER = re.compile(
        r"\b(built|created|designed|architected|launched|shipped|open.?source|"
        r"side project|personal project|hackathon)\b", re.I
    )
    _MAINTAINER = re.compile(
        r"\b(maintained|support|legacy|on-call|oncall|incident|monitoring|"
        r"ops|operations|maintenance)\b", re.I
    )
    builder_hits    = len(_BUILDER.findall(all_text))
    maintainer_hits = len(_MAINTAINER.findall(all_text))
    if builder_hits > maintainer_hits and builder_hits >= 2:
        signals["builder_vs_maintainer"] = "builder"
    elif maintainer_hits > builder_hits and maintainer_hits >= 2:
        signals["builder_vs_maintainer"] = "maintainer"

    # industries
    _INDUSTRY_MAP = {
        "fintech":    re.compile(r"\b(fintech|payments?|banking|neobank|insurance|lending|credit)\b", re.I),
        "healthtech": re.compile(r"\b(healthtech|health.?tech|health.?care|medical|hospital|pharma|clinical)\b", re.I),
        "edtech":     re.compile(r"\b(edtech|education|e-?learning|lms|tutoring|upskill)\b", re.I),
        "ecommerce":  re.compile(r"\b(e-?commerce|retail|marketplace|d2c|direct.to.consumer)\b", re.I),
        "saas":       re.compile(r"\b(saas|b2b\s*saas|enterprise\s*software|crm|erp)\b", re.I),
        "ai/ml":      re.compile(r"\b(ai|machine.?learning|deep.?learning|nlp|llm|data.?science|ml.?engineer)\b", re.I),
        "logistics":  re.compile(r"\b(logistics|supply.chain|warehouse|fulfillment|delivery)\b", re.I),
        "infra":      re.compile(r"\b(infra(structure)?|devops|platform|cloud|kubernetes|sre)\b", re.I),
    }
    corp_text = " ".join(
        (exp.get("companyName") or exp.get("company") or "") + " "
        + (exp.get("description") or "") + " " + (exp.get("title") or "")
        for exp in all_exp_list
    )
    found_industries: list[str] = []
    for industry, pat in _INDUSTRY_MAP.items():
        if pat.search(corp_text):
            found_industries.append(industry)
    if found_industries:
        signals["industries"] = found_industries

    log.info(
        "LinkedIn profile mapped — %d signals: %s",
        len(signals),
        sorted(signals.keys()),
    )
    return signals


async def parse_linkedin_profile(url: str, api_key: str) -> dict[str, Any]:
    """
    Fetch a LinkedIn profile via LinkdAPI (linkdapi.com) and return structured
    candidate signals.

    LinkdAPI accepts the LinkedIn username (slug) as `username` query param.
    Auth header: X-linkdapi-apikey.
    Returns {} on any failure.
    """
    url = _canonicalise(url)
    username = _extract_username(url)
    if not username:
        log.warning("Could not extract LinkedIn username from URL: %s", url)
        return {}

    if not api_key:
        return {}

    log.info("LinkdAPI: fetching profile for username=%s", username)
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                LINKDAPI_ENDPOINT,
                params={"username": username},
                headers={"X-linkdapi-apikey": api_key},
            )
    except Exception:
        log.exception("LinkdAPI HTTP request failed for username=%s", username)
        return {}

    log.info("LinkdAPI: HTTP %d for username=%s", resp.status_code, username)

    if resp.status_code == 404:
        log.warning("LinkdAPI: profile not found (404) for username=%s", username)
        return {}

    if resp.status_code == 401:
        log.error(
            "LinkdAPI: 401 Unauthorized — check that LINKDAPI_API_KEY is set to a valid "
            "key from https://linkdapi.com"
        )
        return {}

    if resp.status_code == 402:
        log.error("LinkdAPI: 402 Payment Required — account has no credits. Check https://linkdapi.com")
        return {}

    if resp.status_code == 429:
        log.warning("LinkdAPI: 429 rate limit for username=%s", username)
        return {}

    if not resp.is_success:
        log.warning("LinkdAPI: %d for username=%s — body: %s", resp.status_code, username, resp.text[:500])
        return {}

    try:
        data = resp.json()
    except Exception:
        log.exception("LinkdAPI: response JSON parse failed — body: %s", resp.text[:300])
        return {}

    log.info("LinkdAPI: response keys=%s", list(data.keys()) if isinstance(data, dict) else type(data).__name__)

    if not isinstance(data, dict):
        log.warning("LinkdAPI: expected dict, got %s", type(data).__name__)
        return {}

    # LinkdAPI wraps profile data in a "data" envelope: {success, statusCode, message, data: {...}}
    if "data" in data and isinstance(data["data"], dict):
        data = data["data"]
        log.info("LinkdAPI: unwrapped envelope — profile keys=%s", list(data.keys()))

    if not data.get("firstName") and not data.get("lastName") and not data.get("fullName"):
        log.warning("LinkdAPI: profile has no name fields for username=%s — raw: %s", username, str(data)[:400])
        return {}

    return _map_linkdapi_to_signals(data, url)
