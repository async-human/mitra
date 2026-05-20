"""
mitra_api/tools/linkedin_parser.py

Fetches and parses a LinkedIn profile URL into structured candidate signals.

Flow
----
1. Candidate shares their LinkedIn URL in WhatsApp chat
2. Orchestrator detects the URL via regex and calls parse_linkedin_profile()
3. If PROXYCURL_API_KEY is configured: Proxycurl (nubela.co) API fetches the profile JSON
4. Signals are extracted and mapped to the same schema as resume_parser.py
5. Signals are merged into the candidate session (no re-asking of extracted facts)

Graceful degradation
--------------------
- No PROXYCURL_API_KEY → returns {} (orchestrator falls back to manual ask)
- Proxycurl rate limit / error → returns {} with a warning log
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

# Proxycurl API (nubela.co) — accepts a LinkedIn profile URL via the `url` query param.
# Auth: Bearer token from https://nubela.co (same key as PROXYCURL_API_KEY).
# Docs: https://nubela.co/proxycurl/api/v2/linkedin
PROXYCURL_ENDPOINT = "https://nubela.co/proxycurl/api/v2/linkedin"


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


def _map_proxycurl_to_signals(data: dict[str, Any], url: str) -> dict[str, Any]:
    """
    Map a Proxycurl profile JSON to the Mitra candidate signal schema.
    Only includes fields with real data; never guesses or fills defaults.
    """
    signals: dict[str, Any] = {}

    # Always store the URL itself
    signals["linkedin"] = url

    # ── Basic identity ────────────────────────────────────────────────────────
    first = (data.get("first_name") or "").strip()
    last  = (data.get("last_name")  or "").strip()
    full  = f"{first} {last}".strip()
    if full:
        signals["candidate_name"] = full

    headline = (data.get("headline") or "").strip()
    if headline:
        signals["current_role"] = headline

    location = (data.get("city") or data.get("country_full_name") or "").strip()
    if location:
        signals["location"] = location

    summary = (data.get("summary") or "").strip()

    # ── Current company (most recent experience) ──────────────────────────────
    experiences: list[dict] = data.get("experiences") or []
    current_company = ""
    current_title   = ""
    previous_companies: list[str] = []

    # Sort: still-active roles first (ends_at is None), then by start date desc
    def _exp_sort_key(e: dict) -> tuple:
        ends = e.get("ends_at")
        # Ongoing roles float to top
        still_active = 0 if ends is None else 1
        start = e.get("starts_at") or {}
        return (still_active, -(start.get("year") or 0), -(start.get("month") or 0))

    sorted_exp = sorted(experiences, key=_exp_sort_key)

    total_months = 0
    tenure_list: list[int] = []  # months per role, for stability_seeking

    for exp in sorted_exp:
        company = (exp.get("company") or "").strip()
        title   = (exp.get("title")   or "").strip()
        starts  = exp.get("starts_at") or {}
        ends    = exp.get("ends_at")   or {}

        # Compute tenure in months
        start_y = starts.get("year",  0)
        start_m = starts.get("month", 1)
        if ends:
            end_y = ends.get("year",  0)
            end_m = ends.get("month", 1)
        else:
            from datetime import date
            today = date.today()
            end_y, end_m = today.year, today.month

        if start_y:
            months = max(0, (end_y - start_y) * 12 + (end_m - start_m))
            total_months += months
            tenure_list.append(months)

        if not current_company and company:
            current_company = company
            current_title   = title or current_title
        elif company and company != current_company:
            if company not in previous_companies:
                previous_companies.append(company)

    if current_company:
        signals["current_company"] = current_company
    if current_title:
        signals["current_role"] = current_title
    if previous_companies:
        signals["previous_companies"] = previous_companies[:8]  # cap list length

    # ── Years of experience ───────────────────────────────────────────────────
    if total_months > 0:
        signals["years_experience"] = round(total_months / 12, 1)

    # ── Education ─────────────────────────────────────────────────────────────
    educations: list[dict] = data.get("education") or []
    if educations:
        top = educations[0]
        school  = (top.get("school")       or "").strip()
        degree  = (top.get("degree_name")  or "").strip()
        field   = (top.get("field_of_study") or "").strip()
        parts = [p for p in [degree, field, school] if p]
        if parts:
            signals["education"] = ", ".join(parts)

    # ── Tech stack — from skills section ─────────────────────────────────────
    skills_raw: list[dict | str] = data.get("skills") or []
    skill_names: list[str] = []
    for s in skills_raw:
        name = s if isinstance(s, str) else (s.get("name") or "")
        name = name.strip()
        if name:
            skill_names.append(name)

    # Separate technical from soft/generic skills (simple heuristic)
    _SOFT = {"communication", "leadership", "teamwork", "management",
             "problem solving", "analytical", "microsoft office", "excel",
             "presentation", "time management", "project management"}
    tech_skills = [s for s in skill_names if s.lower() not in _SOFT]
    if len(tech_skills) >= 2:
        signals["primary_stack"] = tech_skills[:12]
        if len(tech_skills) > 12:
            signals["secondary_stack"] = tech_skills[12:20]

    # ── GitHub ────────────────────────────────────────────────────────────────
    websites: list[dict] = data.get("websites") or []
    for w in websites:
        url_w = (w if isinstance(w, str) else w.get("url") or "").strip()
        if "github.com" in url_w.lower():
            signals["github"] = url_w
            break

    # ── Behavioral signals — inferred conservatively ──────────────────────────

    # startup_experience: any company in the profile is tagged as startup/seed/series
    company_types: list[str] = []
    for exp in sorted_exp:
        ct = (exp.get("company_linkedin_profile_url") or "")
        # Proxycurl sometimes surfaces company size; fall back to heuristic
        desc = (exp.get("description") or "").lower()
        if any(kw in desc for kw in ("startup", "seed", "series a", "series b", "founded by")):
            company_types.append("startup")
    signals["has_startup_experience"] = len(company_types) > 0

    # leadership: any title containing lead/head/vp/director/principal/staff/architect
    _LEAD_TITLES = re.compile(
        r"\b(lead|head|vp|vice president|director|principal|staff|architect|"
        r"co-founder|cofounder|cto|ceo|founder)\b",
        re.I,
    )
    has_leadership = any(
        _LEAD_TITLES.search(exp.get("title") or "") for exp in sorted_exp
    )
    signals["has_leadership_experience"] = has_leadership

    # stability_seeking: based on median tenure across last 3 roles
    if len(tenure_list) >= 2:
        recent = tenure_list[:3]
        median_months = sorted(recent)[len(recent) // 2]
        if median_months >= 36:
            signals["stability_seeking"] = "high"
        elif median_months <= 14:
            signals["stability_seeking"] = "low"
        # omit "medium" — not distinctive enough to be worth including

    # first_startup_move: all prior companies are large enterprises (no startup exp)
    _ENTERPRISE = re.compile(
        r"\b(tcs|infosys|wipro|accenture|cognizant|ibm|capgemini|hcl|"
        r"google|amazon|microsoft|meta|apple|netflix|salesforce|oracle|"
        r"sap|deloitte|pwc|ey|kpmg)\b",
        re.I,
    )
    all_companies = [current_company] + previous_companies
    if all_companies and not signals.get("has_startup_experience"):
        enterprise_count = sum(
            1 for c in all_companies if c and _ENTERPRISE.search(c)
        )
        if enterprise_count == len([c for c in all_companies if c]):
            signals["first_startup_move"] = True

    # ownership_mindset: founding / first-eng / solo-built in any title or description
    _OWNERSHIP_HIGH = re.compile(
        r"\b(co-?founder|founding engineer|first engineer|"
        r"built from scratch|0.?to.?1|sole developer|solo)\b",
        re.I,
    )
    all_text = " ".join(
        (exp.get("title") or "") + " " + (exp.get("description") or "")
        for exp in sorted_exp
    ) + " " + summary
    if _OWNERSHIP_HIGH.search(all_text):
        signals["ownership_mindset"] = "high"
    elif len(sorted_exp) >= 2:
        # Pure IC at multiple large cos → low (only if no ownership signals anywhere)
        all_titles = " ".join(exp.get("title") or "" for exp in sorted_exp)
        if not re.search(r"\b(lead|architect|principal|staff|head|director|founder)\b", all_titles, re.I):
            signals["ownership_mindset"] = "low"

    # builder_vs_maintainer
    _BUILDER = re.compile(
        r"\b(built|created|designed|architected|launched|shipped|open.?source|"
        r"side project|personal project|hackathon)\b",
        re.I,
    )
    _MAINTAINER = re.compile(
        r"\b(maintained|support|legacy|on-call|oncall|incident|monitoring|"
        r"ops|operations|maintenance)\b",
        re.I,
    )
    builder_hits    = len(_BUILDER.findall(all_text))
    maintainer_hits = len(_MAINTAINER.findall(all_text))
    if builder_hits > maintainer_hits and builder_hits >= 2:
        signals["builder_vs_maintainer"] = "builder"
    elif maintainer_hits > builder_hits and maintainer_hits >= 2:
        signals["builder_vs_maintainer"] = "maintainer"

    # industries: extract from experience descriptions / company names
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
    found_industries: list[str] = []
    corp_text = " ".join(
        (exp.get("company") or "") + " " + (exp.get("description") or "") + " " + (exp.get("title") or "")
        for exp in sorted_exp
    )
    for industry, pat in _INDUSTRY_MAP.items():
        if pat.search(corp_text) and industry not in found_industries:
            found_industries.append(industry)
    if found_industries:
        signals["industries"] = found_industries

    # ── Notable projects — from projects section or top accomplishment ─────────
    projects: list[dict] = data.get("accomplishment_projects") or []
    if projects:
        top_proj = projects[0]
        proj_title = (top_proj.get("title") or "").strip()
        proj_desc  = (top_proj.get("description") or "").strip()[:200]
        if proj_title:
            signals["notable_projects"] = f"{proj_title}: {proj_desc}".strip(": ")

    log.info(
        "LinkedIn profile mapped — %d signals: %s",
        len(signals),
        sorted(signals.keys()),
    )
    return signals


async def parse_linkedin_profile(url: str, api_key: str) -> dict[str, Any]:
    """
    Fetch a LinkedIn profile via Proxycurl (nubela.co) and return structured
    candidate signals.

    The Proxycurl API accepts a LinkedIn profile URL as the `url` query parameter.
    Returns {} on any failure.
    """
    url = _canonicalise(url)

    if not api_key:
        return {}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                PROXYCURL_ENDPOINT,
                params={"url": url},
                headers={"Authorization": f"Bearer {api_key}"},
            )
    except Exception:
        log.exception("Proxycurl HTTP request failed for %s", url)
        return {}

    if resp.status_code == 404:
        log.warning("LinkedIn profile not found (404): %s", url)
        return {}

    if resp.status_code == 410:
        log.error(
            "Proxycurl returned 410 — API endpoint may have changed. "
            "Check https://nubela.co/proxycurl/api/v2/linkedin for the current endpoint."
        )
        return {}

    if resp.status_code == 401:
        log.error(
            "Proxycurl returned 401 Unauthorized — check that PROXYCURL_API_KEY is set "
            "to a valid key from https://nubela.co"
        )
        return {}

    if resp.status_code == 429:
        log.warning("Proxycurl rate limit — skipping LinkedIn parse for %s", url)
        return {}

    if not resp.is_success:
        log.warning("Proxycurl returned %d for %s: %s", resp.status_code, url, resp.text[:300])
        return {}

    try:
        data = resp.json()
    except Exception:
        log.exception("Proxycurl response JSON parse failed")
        return {}

    if not isinstance(data, dict) or not data.get("first_name"):
        log.warning("Proxycurl returned unexpected shape for %s: %s", url, str(data)[:200])
        return {}

    return _map_proxycurl_to_signals(data, url)
