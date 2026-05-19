"""
mitra_api/tools/fit_score.py

Dimensional fit scoring — now delegates to the compatibility engine.

Returns the legacy 4-key dict (salary_fit, location_fit, skill_fit, overall_fit)
plus all 8 compatibility dimensions and the compatibility decision.

All scores default to 0.5 when either side is missing data, so unknown ≠ bad.
"""

from __future__ import annotations

from typing import Any


def compute_fit_scores(
    signals: dict[str, Any],
    job_salary_min: int | None,
    job_salary_max: int | None,
    job_location: str | None,
    job_remote_policy: str | None,
    job_stack: list[str] | None,
    job_title: str | None = None,
    job_stage: str | None = None,
    job_sector: str | None = None,
    founder_profile: dict[str, Any] | None = None,
) -> dict[str, float]:
    """
    Returns salary_fit, location_fit, skill_fit, overall_fit (legacy keys) plus
    all 8 compatibility dimensions and compatibility_decision.
    """
    from mitra_api.tools.compatibility import compute_compatibility

    job_dict = {
        "salary_min_lpa":  job_salary_min,
        "salary_max_lpa":  job_salary_max,
        "location":        job_location,
        "remote_policy":   job_remote_policy,
        "stack":           job_stack,
        "title":           job_title or "",
        "stage":           job_stage or "",
        "sector":          job_sector or "",
    }
    compat = compute_compatibility(signals, job_dict, founder_profile or {})
    dims = compat["dimensions"]

    return {
        # Legacy keys — kept for all existing callers
        "salary_fit":   dims["salary_fit"],
        "location_fit": dims["location_fit"],
        "skill_fit":    dims["skill_fit"],
        "overall_fit":  compat["overall_score"],
        # Expanded dimensions
        "seniority_fit":          dims["seniority_fit"],
        "motivation_fit":         dims["motivation_fit"],
        "ownership_fit":          dims["ownership_fit"],
        "startup_readiness_fit":  dims["startup_readiness_fit"],
        "founder_style_fit":      dims["founder_style_fit"],
        # Decision
        "compatibility_decision": compat["decision"],
        "compatibility_score":    compat["overall_score"],
        "risk_flags":             compat["risk_flags"],
        "why":                    compat["why"],
    }

