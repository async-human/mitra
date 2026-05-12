"""
mitra_api/tools/fit_score.py

Dimensional fit scoring — pure functions, no DB or LLM required.

Scores are 0.0 (no fit) to 1.0 (perfect fit).

salary_fit    — does the candidate's expectation fall within the job's range?
location_fit  — does the candidate's location preference match the job?
skill_fit     — what fraction of the job's required stack does the candidate cover?
overall_fit   — weighted average (salary 40%, location 30%, skill 30%)

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
) -> dict[str, float]:
    """
    Returns salary_fit, location_fit, skill_fit, overall_fit — all floats 0.0–1.0.
    Call this after loading candidate signals and the job row.
    """
    return {
        "salary_fit":   _salary_fit(signals, job_salary_min, job_salary_max),
        "location_fit": _location_fit(signals, job_location, job_remote_policy),
        "skill_fit":    _skill_fit(signals, job_stack),
        "overall_fit":  _overall(signals, job_salary_min, job_salary_max,
                                 job_location, job_remote_policy, job_stack),
    }


# ── Salary ─────────────────────────────────────────────────────────────────────

def _salary_fit(
    signals: dict[str, Any],
    job_min: int | None,
    job_max: int | None,
) -> float:
    target = (
        signals.get("salary_target_lpa")
        or signals.get("salary_floor_lpa")
        or signals.get("salary_min_lpa")
        or signals.get("current_ctc_lpa")
    )
    if not target or not job_max:
        return 0.5  # unknown — stay neutral

    try:
        target = float(target)
        job_max = float(job_max)
        job_min = float(job_min or job_max * 0.7)
    except (TypeError, ValueError):
        return 0.5

    if target <= job_min:
        return 1.0                         # well within range
    if target <= job_max:
        # Linearly scale from 1.0 (at min) to 0.7 (at max)
        ratio = (target - job_min) / max(job_max - job_min, 1)
        return round(1.0 - 0.3 * ratio, 3)
    if target <= job_max * 1.10:
        return 0.4                         # slightly over — negotiable
    if target <= job_max * 1.25:
        return 0.2                         # meaningfully over
    return 0.0                             # hard miss


# ── Location ───────────────────────────────────────────────────────────────────

def _location_fit(
    signals: dict[str, Any],
    job_location: str | None,
    job_remote_policy: str | None,
) -> float:
    policy = (job_remote_policy or "").lower()
    if policy == "remote":
        return 1.0  # fully remote always fits

    prefs: list[str] = signals.get("location_preference", [])
    if isinstance(prefs, str):
        prefs = [prefs]
    prefs = [p.strip().lower() for p in prefs if p]

    if not prefs:
        return 0.5  # candidate hasn't stated preference — stay neutral

    # If candidate explicitly accepts remote/hybrid, hybrid jobs still work
    if policy == "hybrid" and any(p in ("remote", "hybrid") for p in prefs):
        return 0.85

    loc = (job_location or "").lower()
    if any(p in loc or p == "remote" for p in prefs):
        return 1.0

    # Check city-level overlap (e.g. "bengaluru" in "Bengaluru, Karnataka")
    for pref in prefs:
        for city_token in loc.split(","):
            if pref in city_token.strip():
                return 1.0

    return 0.1  # location mismatch is a near-dealbreaker


# ── Skill ──────────────────────────────────────────────────────────────────────

def _skill_fit(
    signals: dict[str, Any],
    job_stack: list[str] | None,
) -> float:
    raw = signals.get("primary_stack", [])
    if isinstance(raw, str):
        candidate_stack = {s.strip().lower() for s in raw.split(",") if s.strip()}
    elif isinstance(raw, list):
        candidate_stack = {str(s).lower() for s in raw}
    else:
        candidate_stack = set()

    if isinstance(job_stack, list):
        required = {str(s).lower() for s in job_stack}
    else:
        required = set()

    if not candidate_stack or not required:
        return 0.5  # insufficient data — stay neutral

    overlap = len(candidate_stack & required)
    # Score = overlap / required, capped at 1.0, with diminishing returns above 50%
    raw_score = overlap / len(required)
    return round(min(1.0, raw_score), 3)


# ── Overall ────────────────────────────────────────────────────────────────────

def _overall(signals, job_min, job_max, job_location, job_remote, job_stack) -> float:
    s = _salary_fit(signals, job_min, job_max)
    l = _location_fit(signals, job_location, job_remote)
    k = _skill_fit(signals, job_stack)
    # Location is weighted highest — it's the hardest dealbreaker in India
    return round(s * 0.35 + l * 0.35 + k * 0.30, 3)
