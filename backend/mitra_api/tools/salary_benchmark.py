"""
mitra_api/tools/salary_benchmark.py

Three-tier salary benchmark lookup (highest fidelity first):

  Tier 1 — Live jobs table
    Query active jobs that match the role/stage, compute P25/median/P75
    from actual salary_min_lpa / salary_max_lpa data founders submitted.
    Used when we have ≥ MIN_JOBS_FOR_LIVE data points.

  Tier 2 — salary_benchmarks DB table
    Admin-updatable rows, seeded from survey data (Levels.fyi India, AIM,
    NASSCOM, AngelList India talent reports). Updated quarterly via admin API
    or direct DB edit — no deployment needed.

  Tier 3 — Hardcoded fallback
    Only used on first boot before the DB table is seeded, or for combinations
    not in the DB. Should never be the steady-state path in production.
"""

from __future__ import annotations

import logging
import statistics
from typing import Any

log = logging.getLogger(__name__)

MIN_JOBS_FOR_LIVE = 3   # minimum data points before trusting live computation

# ── Role / stage / seniority normalisation ────────────────────────────────────

_ROLE_MAP: dict[str, str] = {
    "backend":          "backend_engineer",
    "python":           "backend_engineer",
    "java":             "backend_engineer",
    "go":               "backend_engineer",
    "node":             "backend_engineer",
    "api":              "backend_engineer",
    "fullstack":        "backend_engineer",
    "full stack":       "backend_engineer",
    "full-stack":       "backend_engineer",
    "ml":               "ml_engineer",
    "machine learning": "ml_engineer",
    "data science":     "ml_engineer",
    "ai engineer":      "ml_engineer",
    "llm":              "ml_engineer",
    "frontend":         "frontend_engineer",
    "react":            "frontend_engineer",
    "vue":              "frontend_engineer",
    "angular":          "frontend_engineer",
    "typescript":       "frontend_engineer",
    "data engineer":    "data_engineer",
    "dbt":              "data_engineer",
    "spark":            "data_engineer",
    "analytics engineer": "data_engineer",
    "devops":           "devops_platform",
    "platform":         "devops_platform",
    "sre":              "devops_platform",
    "kubernetes":       "devops_platform",
    "infra":            "devops_platform",
    "cloud":            "devops_platform",
    "security":         "security_engineer",
    "appsec":           "security_engineer",
    "mobile":           "mobile_engineer",
    "ios":              "mobile_engineer",
    "android":          "mobile_engineer",
    "flutter":          "mobile_engineer",
}

_STAGE_MAP: dict[str, str] = {
    "pre-seed":  "seed",
    "pre seed":  "seed",
    "seed":      "seed",
    "series a":  "series_a",
    "series-a":  "series_a",
    "series b":  "series_b",
    "series-b":  "series_b",
    "series c":  "series_c_plus",
    "series-c":  "series_c_plus",
    "series d":  "series_c_plus",
    "late stage":"series_c_plus",
    "growth":    "series_c_plus",
    "bootstrapped": "seed",
}

_SENIORITY_MAP: dict[str, str] = {
    "intern":    "mid",
    "junior":    "mid",
    "mid":       "mid",
    "senior":    "senior",
    "sr.":       "senior",
    "sr ":       "senior",
    "lead":      "lead",
    "staff":     "lead",
    "principal": "principal",
    "architect": "principal",
    "director":  "principal",
}


def _normalise(role: str, stage: str, seniority: str) -> tuple[str, str, str]:
    r = role.lower().strip()
    st = stage.lower().strip()
    se = seniority.lower().strip()
    role_key      = next((v for k, v in _ROLE_MAP.items()      if k in r),  "backend_engineer")
    stage_key     = next((v for k, v in _STAGE_MAP.items()     if k in st), "series_a")
    seniority_key = next((v for k, v in _SENIORITY_MAP.items() if k in se), "senior")
    return role_key, stage_key, seniority_key


# ── Tier 3: hardcoded fallback ─────────────────────────────────────────────────
# Kept minimal — only used before DB is seeded.

_FALLBACK: dict[str, dict[str, dict[str, dict[str, int]]]] = {
    "backend_engineer": {
        "seed":         {"mid": {"p25":14,"median":18,"p75":24}, "senior": {"p25":20,"median":26,"p75":34}, "lead": {"p25":28,"median":36,"p75":48}, "principal": {"p25":38,"median":50,"p75":65}},
        "series_a":     {"mid": {"p25":16,"median":22,"p75":28}, "senior": {"p25":24,"median":32,"p75":42}, "lead": {"p25":34,"median":45,"p75":58}, "principal": {"p25":45,"median":60,"p75":80}},
        "series_b":     {"mid": {"p25":20,"median":28,"p75":36}, "senior": {"p25":30,"median":42,"p75":56}, "lead": {"p25":42,"median":56,"p75":75}, "principal": {"p25":55,"median":75,"p75":100}},
        "series_c_plus":{"mid": {"p25":24,"median":34,"p75":44}, "senior": {"p25":38,"median":52,"p75":68}, "lead": {"p25":52,"median":70,"p75":90}, "principal": {"p25":65,"median":90,"p75":120}},
    },
    "ml_engineer": {
        "seed":         {"mid": {"p25":16,"median":22,"p75":30}, "senior": {"p25":24,"median":32,"p75":44}, "lead": {"p25":35,"median":48,"p75":65}},
        "series_a":     {"mid": {"p25":20,"median":28,"p75":38}, "senior": {"p25":30,"median":42,"p75":56}, "lead": {"p25":42,"median":58,"p75":78}},
        "series_b":     {"mid": {"p25":26,"median":36,"p75":48}, "senior": {"p25":38,"median":52,"p75":70}, "lead": {"p25":52,"median":72,"p75":95}},
        "series_c_plus":{"mid": {"p25":32,"median":45,"p75":60}, "senior": {"p25":48,"median":65,"p75":88}, "lead": {"p25":65,"median":88,"p75":115}},
    },
    "frontend_engineer": {
        "seed":         {"mid": {"p25":12,"median":16,"p75":22}, "senior": {"p25":18,"median":24,"p75":32}, "lead": {"p25":26,"median":34,"p75":46}},
        "series_a":     {"mid": {"p25":14,"median":20,"p75":26}, "senior": {"p25":22,"median":30,"p75":40}, "lead": {"p25":30,"median":42,"p75":56}},
        "series_b":     {"mid": {"p25":18,"median":25,"p75":34}, "senior": {"p25":28,"median":38,"p75":50}, "lead": {"p25":38,"median":52,"p75":68}},
        "series_c_plus":{"mid": {"p25":22,"median":30,"p75":40}, "senior": {"p25":34,"median":46,"p75":62}, "lead": {"p25":46,"median":62,"p75":82}},
    },
    "data_engineer": {
        "seed":         {"mid": {"p25":14,"median":18,"p75":24}, "senior": {"p25":20,"median":28,"p75":38}, "lead": {"p25":30,"median":40,"p75":54}},
        "series_a":     {"mid": {"p25":16,"median":22,"p75":30}, "senior": {"p25":24,"median":34,"p75":46}, "lead": {"p25":36,"median":50,"p75":68}},
        "series_b":     {"mid": {"p25":20,"median":28,"p75":38}, "senior": {"p25":30,"median":42,"p75":58}, "lead": {"p25":44,"median":60,"p75":80}},
        "series_c_plus":{"mid": {"p25":25,"median":35,"p75":48}, "senior": {"p25":38,"median":52,"p75":70}, "lead": {"p25":55,"median":74,"p75":98}},
    },
    "devops_platform": {
        "seed":         {"mid": {"p25":14,"median":20,"p75":28}, "senior": {"p25":22,"median":30,"p75":42}, "lead": {"p25":32,"median":44,"p75":60}},
        "series_a":     {"mid": {"p25":18,"median":24,"p75":32}, "senior": {"p25":26,"median":36,"p75":50}, "lead": {"p25":38,"median":52,"p75":70}},
        "series_b":     {"mid": {"p25":22,"median":30,"p75":40}, "senior": {"p25":32,"median":45,"p75":62}, "lead": {"p25":48,"median":65,"p75":86}},
        "series_c_plus":{"mid": {"p25":28,"median":38,"p75":50}, "senior": {"p25":40,"median":56,"p75":76}, "lead": {"p25":60,"median":80,"p75":105}},
    },
}


def _fallback_data(role_key: str, stage_key: str, seniority_key: str) -> dict[str, int]:
    d = (
        _FALLBACK.get(role_key, {})
                 .get(stage_key, {})
                 .get(seniority_key)
    )
    if d:
        return d
    return _FALLBACK["backend_engineer"]["series_a"]["senior"]


# ── Tier 1: live computation from jobs table ───────────────────────────────────

async def _live_benchmark(
    role_key: str,
    stage_key: str,
) -> dict[str, int] | None:
    """
    Compute P25/median/P75 from active jobs in the DB that match this
    role category and stage. Returns None if fewer than MIN_JOBS_FOR_LIVE points.
    """
    try:
        from sqlalchemy import select, func as sqlfunc
        from mitra_api.db.engine import get_session_factory
        from mitra_api.db.models import Job

        # Map role_key back to title keywords for a loose ILIKE match
        _ROLE_KEYWORDS: dict[str, list[str]] = {
            "backend_engineer":   ["backend", "python", "java", "go ", "node", "fullstack", "api"],
            "ml_engineer":        ["ml", "machine learning", "ai ", "llm", "data science"],
            "frontend_engineer":  ["frontend", "react", "vue", "angular", "typescript"],
            "data_engineer":      ["data engineer", "analytics engineer", "dbt", "spark"],
            "devops_platform":    ["devops", "platform", "sre", "infra", "cloud", "kubernetes"],
            "security_engineer":  ["security", "appsec"],
            "mobile_engineer":    ["mobile", "ios", "android", "flutter"],
        }
        _STAGE_KEYWORDS: dict[str, list[str]] = {
            "seed":         ["seed", "pre-seed", "bootstrapped"],
            "series_a":     ["series a", "series-a"],
            "series_b":     ["series b", "series-b"],
            "series_c_plus":["series c", "series d", "late", "growth"],
        }

        factory = get_session_factory()
        async with factory() as db:
            # Pull all active jobs with salary data
            rows = (await db.execute(
                select(Job.salary_min_lpa, Job.salary_max_lpa, Job.stage, Job.title)
                .where(
                    Job.status == "active",
                    Job.salary_min_lpa.isnot(None),
                    Job.salary_max_lpa.isnot(None),
                )
            )).all()

        if not rows:
            return None

        keywords_role  = _ROLE_KEYWORDS.get(role_key, [])
        keywords_stage = _STAGE_KEYWORDS.get(stage_key, [])

        midpoints: list[float] = []
        for min_lpa, max_lpa, stage, title in rows:
            title_l = (title or "").lower()
            stage_l = (stage or "").lower()

            role_match  = not keywords_role  or any(k in title_l for k in keywords_role)
            stage_match = not keywords_stage or any(k in stage_l for k in keywords_stage)

            if role_match and stage_match:
                midpoints.append((min_lpa + max_lpa) / 2)

        if len(midpoints) < MIN_JOBS_FOR_LIVE:
            return None

        midpoints.sort()
        n = len(midpoints)
        p25    = int(midpoints[max(0, int(n * 0.25))])
        median = int(statistics.median(midpoints))
        p75    = int(midpoints[min(n - 1, int(n * 0.75))])

        log.info(
            "live salary benchmark: role=%s stage=%s n=%d p25=%d median=%d p75=%d",
            role_key, stage_key, n, p25, median, p75,
        )
        return {"p25": p25, "median": median, "p75": p75, "n": n}

    except Exception:
        log.exception("live salary benchmark query failed")
        return None


# ── Tier 2: DB benchmark table ────────────────────────────────────────────────

async def _db_benchmark(
    role_key: str,
    stage_key: str,
    seniority_key: str,
) -> dict[str, int] | None:
    try:
        from sqlalchemy import select
        from mitra_api.db.engine import get_session_factory
        from mitra_api.db.models import SalaryBenchmark

        factory = get_session_factory()
        async with factory() as db:
            row = (await db.execute(
                select(SalaryBenchmark).where(
                    SalaryBenchmark.role_category == role_key,
                    SalaryBenchmark.stage         == stage_key,
                    SalaryBenchmark.seniority     == seniority_key,
                )
            )).scalar_one_or_none()

        if row:
            return {"p25": row.p25_lpa, "median": row.median_lpa, "p75": row.p75_lpa}
        return None
    except Exception:
        log.exception("DB salary benchmark query failed")
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_salary_benchmark_async(
    role: str,
    stage: str,
    seniority: str,
) -> dict[str, Any]:
    """
    Async version — used by the agent tool runner.
    Tries: live jobs → DB benchmarks → hardcoded fallback.
    """
    role_key, stage_key, seniority_key = _normalise(role, stage, seniority)

    # Tier 1: live data from our own jobs
    data = await _live_benchmark(role_key, stage_key)
    source_label = "Mitra live data"

    # Tier 2: DB-stored benchmarks
    if not data:
        data = await _db_benchmark(role_key, stage_key, seniority_key)
        source_label = "industry survey data"

    # Tier 3: hardcoded fallback
    if not data:
        data = _fallback_data(role_key, stage_key, seniority_key)
        source_label = "reference benchmarks"

    n_note = f" ({data['n']} active roles)" if data.get("n") else ""

    message = (
        f"For a *{seniority.title()} {role.title()}* at a *{stage.title()}* startup in India "
        f"_({source_label}{n_note})_:\n\n"
        f"― Lower end (P25): ₹{data['p25']}L\n"
        f"― Median: ₹{data['median']}L\n"
        f"― Strong offer (P75): ₹{data['p75']}L\n\n"
        f"_CTC including base + variable. Equity/ESOPs are separate._"
    )

    return {
        "role_category": role_key,
        "stage":         stage_key,
        "seniority":     seniority_key,
        "p25_lpa":       data["p25"],
        "median_lpa":    data["median"],
        "p75_lpa":       data["p75"],
        "source":        source_label,
        "data_points":   data.get("n"),
        "message":       message,
    }


def get_salary_benchmark(role: str, stage: str, seniority: str) -> dict[str, Any]:
    """Sync shim — runs the async version via asyncio. Used in legacy sync contexts."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already inside an async context (FastAPI) — caller should use the async version
            role_key, stage_key, seniority_key = _normalise(role, stage, seniority)
            data = _fallback_data(role_key, stage_key, seniority_key)
            return {
                "role_category": role_key, "stage": stage_key, "seniority": seniority_key,
                "p25_lpa": data["p25"], "median_lpa": data["median"], "p75_lpa": data["p75"],
                "source": "reference benchmarks", "message": (
                    f"For a *{seniority.title()} {role.title()}* at a *{stage.title()}* startup:\n"
                    f"P25 ₹{data['p25']}L · Median ₹{data['median']}L · P75 ₹{data['p75']}L"
                ),
            }
        return loop.run_until_complete(get_salary_benchmark_async(role, stage, seniority))
    except Exception:
        role_key, stage_key, seniority_key = _normalise(role, stage, seniority)
        data = _fallback_data(role_key, stage_key, seniority_key)
        return {
            "role_category": role_key, "stage": stage_key, "seniority": seniority_key,
            "p25_lpa": data["p25"], "median_lpa": data["median"], "p75_lpa": data["p75"],
            "source": "reference benchmarks", "message": "",
        }
