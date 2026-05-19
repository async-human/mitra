"""
mitra_api/tools/compatibility.py

Multidimensional compatibility engine — the core decision primitive.

compute_compatibility(signals, job, founder_profile) returns:
{
  "overall_score":  0.82,
  "decision":       "recommend | collect_more | hold | block",
  "dimensions": {
    "salary_fit":           0.80,
    "location_fit":         1.00,
    "skill_fit":            0.75,
    "seniority_fit":        0.85,
    "motivation_fit":       0.90,
    "ownership_fit":        0.70,
    "startup_readiness_fit":0.85,
    "founder_style_fit":    0.65,
  },
  "risk_flags": ["salary near upper band", "first startup move"],
  "why": "Strong technical and motivation fit. ...",
  "role_type": "founding_engineer | senior_ic",
  "weight_profile": {...},
}

All dimension scores default to 0.5 when data is insufficient (unknown ≠ bad).
"""

from __future__ import annotations

from typing import Any


# ── Role-type detection ────────────────────────────────────────────────────────

_FOUNDING_TITLE_SIGNALS = frozenset({
    "founding", "first engineer", "early engineer", "0-1", "0 to 1",
    "staff", "principal", "architect",
})
_LATE_STAGE_SIGNALS = frozenset({"series c", "series d", "series e", "growth", "pre-ipo"})
_EARLY_STAGE_SIGNALS = frozenset({"seed", "pre-seed", "series a"})


def _detect_role_type(job: dict[str, Any]) -> str:
    """Returns 'founding_engineer' or 'senior_ic'."""
    title = (job.get("title") or "").lower()
    stage = (job.get("stage") or "").lower()

    if any(sig in title for sig in _FOUNDING_TITLE_SIGNALS):
        return "founding_engineer"
    if any(sig in stage for sig in _LATE_STAGE_SIGNALS):
        return "senior_ic"
    if any(sig in stage for sig in _EARLY_STAGE_SIGNALS):
        return "founding_engineer"
    # Default: founding unless title screams otherwise
    return "founding_engineer"


# ── Weight profiles ────────────────────────────────────────────────────────────

_WEIGHTS_FOUNDING = {
    "ownership_fit":          0.25,
    "startup_readiness_fit":  0.20,
    "skill_fit":              0.20,
    "salary_fit":             0.15,
    "motivation_fit":         0.10,
    "location_fit":           0.10,
    # seniority_fit and founder_style_fit share the remaining 0.0
    # (folded into overall as unweighted tie-breaker signals)
}

_WEIGHTS_SENIOR_IC = {
    "skill_fit":              0.30,
    "seniority_fit":          0.25,
    "salary_fit":             0.20,
    "location_fit":           0.15,
    "motivation_fit":         0.10,
}

# Dimensions that influence the weighted sum in each role type
_WEIGHTED_DIMS_FOUNDING = [
    "ownership_fit", "startup_readiness_fit", "skill_fit",
    "salary_fit", "motivation_fit", "location_fit",
]
_WEIGHTED_DIMS_SENIOR_IC = [
    "skill_fit", "seniority_fit", "salary_fit", "location_fit", "motivation_fit",
]


# ── Individual dimension scorers ───────────────────────────────────────────────

def _salary_fit(signals: dict[str, Any], job: dict[str, Any]) -> float:
    target = (
        signals.get("salary_target_lpa")
        or signals.get("salary_floor_lpa")
        or signals.get("salary_min_lpa")
        or signals.get("current_ctc_lpa")
    )
    job_max = job.get("salary_max_lpa")
    if not target or not job_max:
        return 0.5
    try:
        target  = float(target)
        job_max = float(job_max)
        job_min = float(job.get("salary_min_lpa") or job_max * 0.7)
    except (TypeError, ValueError):
        return 0.5

    if target <= job_min:
        return 1.0
    if target <= job_max:
        ratio = (target - job_min) / max(job_max - job_min, 1)
        return round(1.0 - 0.3 * ratio, 3)
    if target <= job_max * 1.10:
        return 0.4
    if target <= job_max * 1.25:
        return 0.2
    return 0.0


def _location_fit(signals: dict[str, Any], job: dict[str, Any]) -> float:
    policy = (job.get("remote_policy") or "").lower()
    if policy == "remote":
        return 1.0

    prefs: list[str] = signals.get("location_preference", [])
    if isinstance(prefs, str):
        prefs = [prefs]
    prefs = [p.strip().lower() for p in prefs if p]

    if not prefs:
        return 0.5

    if policy == "hybrid" and any(p in ("remote", "hybrid") for p in prefs):
        return 0.85

    loc = (job.get("location") or "").lower()
    if any(p in loc or p == "remote" for p in prefs):
        return 1.0
    for pref in prefs:
        for city_token in loc.split(","):
            if pref in city_token.strip():
                return 1.0
    return 0.1


def _skill_fit(signals: dict[str, Any], job: dict[str, Any]) -> float:
    raw = signals.get("primary_stack", [])
    if isinstance(raw, str):
        candidate_stack = {s.strip().lower() for s in raw.split(",") if s.strip()}
    elif isinstance(raw, list):
        candidate_stack = {str(s).lower() for s in raw}
    else:
        candidate_stack = set()

    job_stack = job.get("stack")
    if isinstance(job_stack, list):
        required = {str(s).lower() for s in job_stack}
    else:
        required = set()

    if not candidate_stack or not required:
        return 0.5

    overlap = len(candidate_stack & required)
    return round(min(1.0, overlap / len(required)), 3)


def _seniority_fit(signals: dict[str, Any], job: dict[str, Any]) -> float:
    """Fit between candidate's actual seniority and what the role demands."""
    years = signals.get("years_experience") or signals.get("years_exp")
    try:
        years = float(years) if years is not None else None
    except (TypeError, ValueError):
        years = None

    builder = signals.get("builder_vs_maintainer", "")
    specificity = signals.get("technical_specificity", "")

    title = (job.get("title") or "").lower()
    stage = (job.get("stage") or "").lower()

    # Estimate expected years from role signals
    if any(t in title for t in ("junior", "associate", "entry")):
        expected_range = (0, 3)
    elif any(t in title for t in ("senior", "lead", "principal", "staff", "architect")):
        expected_range = (5, 15)
    elif any(t in title for t in ("founding", "first engineer")):
        expected_range = (4, 12)
    else:
        expected_range = (2, 8)  # mid-level default

    if years is None:
        # Fall back to behavioral signals
        if str(builder).lower() in ("builder", "high") or str(specificity).lower() in ("high", "deep"):
            return 0.75
        return 0.5

    lo, hi = expected_range
    if lo <= years <= hi:
        return 1.0
    if years < lo:
        # too junior — score drops proportionally
        gap = lo - years
        return max(0.0, round(1.0 - gap * 0.15, 3))
    # too senior — slight penalty but founders sometimes love over-qualified
    gap = years - hi
    return max(0.3, round(1.0 - gap * 0.08, 3))


def _motivation_fit(signals: dict[str, Any], job: dict[str, Any]) -> float:
    """Does what the candidate wants align with what the job offers?"""
    motivation = signals.get("motivation") or signals.get("what_they_want") or ""
    if isinstance(motivation, list):
        motivation = " ".join(str(m) for m in motivation)
    motivation = str(motivation).lower()

    career_push = str(signals.get("career_push") or "").lower()
    career_pull = str(signals.get("career_pull") or "").lower()

    stage = (job.get("stage") or "").lower()
    sector = (job.get("sector") or "").lower()

    if not motivation and not career_pull:
        return 0.5

    score = 0.5
    combined = f"{motivation} {career_push} {career_pull}"

    # Startup-aligned motivations
    if any(kw in combined for kw in ("build", "product", "impact", "ownership", "0 to 1", "0-1", "founding")):
        score += 0.2
    # Stage alignment
    if any(sig in stage for sig in _EARLY_STAGE_SIGNALS) and any(
        kw in combined for kw in ("early", "seed", "founding", "startup")
    ):
        score += 0.15
    # Domain interest
    if sector and any(word in combined for word in sector.split()):
        score += 0.15
    # Anti-signals
    if any(kw in combined for kw in ("stability", "safe", "big company", "faang", "brand name")):
        score -= 0.2

    return round(max(0.0, min(1.0, score)), 3)


def _ownership_fit(signals: dict[str, Any], job: dict[str, Any]) -> float:
    """Ownership mindset alignment — critical for founding/early roles."""
    ownership = str(signals.get("ownership_mindset") or "").lower()
    risk = str(signals.get("risk_tolerance") or "").lower()
    stability = str(signals.get("stability_seeking") or "").lower()
    first_startup = signals.get("first_startup_move")

    score = 0.5

    # Positive ownership signals
    if ownership in ("high", "strong", "yes", "true"):
        score += 0.25
    elif ownership in ("medium", "moderate"):
        score += 0.05
    elif ownership in ("low", "no", "false"):
        score -= 0.20

    # Risk tolerance
    if risk in ("high", "comfortable", "yes"):
        score += 0.10
    elif risk in ("low", "risk_averse", "no"):
        score -= 0.15

    # Stability-seeking is an anti-signal for startup roles
    if stability in ("high", "yes", "true"):
        score -= 0.15

    # First startup move — slight caution but not a block
    if first_startup in (True, "true", "yes", 1):
        score -= 0.05

    return round(max(0.0, min(1.0, score)), 3)


def _startup_readiness_fit(signals: dict[str, Any], job: dict[str, Any]) -> float:
    """Is the candidate genuinely ready for startup life?"""
    first_startup = signals.get("first_startup_move")
    risk = str(signals.get("risk_tolerance") or "").lower()
    stability = str(signals.get("stability_seeking") or "").lower()
    startup_stage_pref = signals.get("startup_stage_pref") or []
    if isinstance(startup_stage_pref, str):
        startup_stage_pref = [startup_stage_pref]
    stage_prefs_lower = [str(s).lower() for s in startup_stage_pref]

    job_stage = (job.get("stage") or "").lower()

    score = 0.6  # moderate default — most people open to startups

    # Prior startup experience
    current_company = str(signals.get("current_company") or "").lower()
    if any(kw in current_company for kw in ("startup", "seed", "series")):
        score += 0.15

    # Explicit stage preference match
    if job_stage and any(job_stage in pref or pref in job_stage for pref in stage_prefs_lower):
        score += 0.15

    # First-time startup mover — real readiness uncertainty
    if first_startup in (True, "true", "yes", 1):
        score -= 0.15

    # Risk aversion lowers startup readiness
    if stability in ("high", "yes", "true"):
        score -= 0.20
    if risk in ("low", "risk_averse"):
        score -= 0.10

    return round(max(0.0, min(1.0, score)), 3)


def _founder_style_fit(signals: dict[str, Any], founder_profile: dict[str, Any]) -> float:
    """How well does the candidate profile match this founder's known preferences?"""
    if not founder_profile:
        return 0.5

    score = 0.5

    # Check explicit accepts and rejects
    responds_to: list[str] = founder_profile.get("responds_to") or []
    rejects_for: list[str] = founder_profile.get("rejects_for") or []

    candidate_stack = signals.get("primary_stack") or []
    if isinstance(candidate_stack, str):
        candidate_stack = [s.strip() for s in candidate_stack.split(",")]
    candidate_stack_lower = [str(s).lower() for s in candidate_stack]

    ownership = str(signals.get("ownership_mindset") or "").lower()
    motivation = str(signals.get("motivation") or "").lower()
    combined_candidate = f"{' '.join(candidate_stack_lower)} {ownership} {motivation}"

    # Positive: candidate matches what founder responds to
    for signal in responds_to:
        if signal.lower() in combined_candidate:
            score += 0.10

    # Negative: candidate matches what founder rejects
    for signal in rejects_for:
        sig_lower = signal.lower()
        # "salary mismatch" — check if salary is a problem
        if "salary" in sig_lower:
            salary_s = _salary_fit(signals, {})  # job=empty → returns 0.5 if no job data
            if salary_s < 0.4:
                score -= 0.15
        elif sig_lower in combined_candidate:
            score -= 0.10

    # Founder trust score — high trust founder is more willing to take bets
    trust_score = founder_profile.get("trust_score", 0.5)
    if trust_score < 0.4:
        # Low-trust founder: conservative; penalize any borderline candidates
        score = score * 0.85

    # Fast-response stack signals — does candidate's stack excite this founder?
    fast_stacks: list[str] = founder_profile.get("fast_response_stack_signals") or []
    if any(fs.lower() in combined_candidate for fs in fast_stacks):
        score += 0.10

    return round(max(0.0, min(1.0, score)), 3)


# ── Risk flag detection ────────────────────────────────────────────────────────

def _detect_risk_flags(
    signals: dict[str, Any],
    job: dict[str, Any],
    dims: dict[str, float],
) -> list[str]:
    flags: list[str] = []

    # Salary near upper band
    target = signals.get("salary_target_lpa") or signals.get("salary_floor_lpa")
    job_max = job.get("salary_max_lpa")
    if target and job_max:
        try:
            ratio = float(target) / float(job_max)
            if 0.90 <= ratio <= 1.10:
                flags.append("salary near upper band")
            elif ratio > 1.10:
                flags.append("salary above max")
        except (TypeError, ValueError):
            pass

    # First startup move
    if signals.get("first_startup_move") in (True, "true", "yes", 1):
        flags.append("first startup move")

    # Stability seeking
    if str(signals.get("stability_seeking") or "").lower() in ("high", "yes", "true"):
        flags.append("stability-seeking candidate")

    # Weak ownership for founding role
    role_type = _detect_role_type(job)
    if role_type == "founding_engineer" and dims.get("ownership_fit", 0.5) < 0.45:
        flags.append("low ownership mindset for founding role")

    # Location mismatch
    if dims.get("location_fit", 0.5) <= 0.1:
        flags.append("location mismatch")

    return flags


# ── Why narrative builder ──────────────────────────────────────────────────────

def _build_why(
    signals: dict[str, Any],
    job: dict[str, Any],
    dims: dict[str, float],
    risk_flags: list[str],
    decision: str,
) -> str:
    parts: list[str] = []

    skill = dims.get("skill_fit", 0.5)
    ownership = dims.get("ownership_fit", 0.5)
    motivation = dims.get("motivation_fit", 0.5)
    salary = dims.get("salary_fit", 0.5)

    if skill >= 0.7:
        stack = signals.get("primary_stack") or []
        if isinstance(stack, list) and stack:
            parts.append(f"Strong stack match ({', '.join(str(s) for s in stack[:3])}).")
        else:
            parts.append("Strong technical fit.")
    elif skill < 0.45:
        parts.append("Stack overlap is limited.")

    if ownership >= 0.7:
        parts.append("Ownership mindset is solid.")
    elif ownership < 0.45:
        parts.append("Ownership signals are weak.")

    if motivation >= 0.7:
        parts.append("Motivation aligns with startup environment.")
    elif motivation < 0.45:
        parts.append("Motivation may not align with early-stage demands.")

    if salary < 0.3:
        parts.append("Salary expectation significantly exceeds the range.")
    elif salary >= 0.85:
        parts.append("Well within salary budget.")

    if risk_flags:
        parts.append(f"Risk notes: {'; '.join(risk_flags)}.")

    if not parts:
        if decision == "recommend":
            return "Balanced fit across all dimensions."
        return "Insufficient signals for a confident recommendation."

    return " ".join(parts)


# ── Public API ─────────────────────────────────────────────────────────────────

def compute_compatibility(
    signals: dict[str, Any],
    job: dict[str, Any],
    founder_profile: dict[str, Any] | None = None,
    outcome_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Compute a full compatibility assessment between a candidate and a job.

    Parameters
    ----------
    signals         : candidate signal dict (from Redis session or DB)
    job             : job dict with keys: title, stage, sector, stack, salary_min_lpa,
                      salary_max_lpa, location, remote_policy
    founder_profile : founder behavioural profile (from job.founder_profile or
                      job.signals["_founder_profile"])
    outcome_weights : optional calibration from historical outcomes (Phase 5)

    Returns
    -------
    dict with overall_score, decision, dimensions, risk_flags, why, role_type, weight_profile
    """
    fp = founder_profile or {}
    role_type = _detect_role_type(job)

    # ── Compute all dimension scores ──────────────────────────────────────────
    dims: dict[str, float] = {
        "salary_fit":            _salary_fit(signals, job),
        "location_fit":          _location_fit(signals, job),
        "skill_fit":             _skill_fit(signals, job),
        "seniority_fit":         _seniority_fit(signals, job),
        "motivation_fit":        _motivation_fit(signals, job),
        "ownership_fit":         _ownership_fit(signals, job),
        "startup_readiness_fit": _startup_readiness_fit(signals, job),
        "founder_style_fit":     _founder_style_fit(signals, fp),
    }

    # ── Select weight profile (role-type aware) ───────────────────────────────
    if role_type == "founding_engineer":
        base_weights = dict(_WEIGHTS_FOUNDING)
        weighted_dims = _WEIGHTED_DIMS_FOUNDING
    else:
        base_weights = dict(_WEIGHTS_SENIOR_IC)
        weighted_dims = _WEIGHTED_DIMS_SENIOR_IC

    # Apply optional outcome-calibrated weight overrides (Phase 5)
    if outcome_weights:
        for k, v in outcome_weights.items():
            if k in base_weights:
                base_weights[k] = v

    # ── Compute weighted overall score ────────────────────────────────────────
    total_weight = sum(base_weights.get(d, 0.0) for d in weighted_dims)
    if total_weight > 0:
        overall = sum(
            dims[d] * base_weights.get(d, 0.0) for d in weighted_dims
        ) / total_weight
    else:
        overall = sum(dims.values()) / len(dims)

    overall = round(overall, 3)

    # ── Hard block conditions ─────────────────────────────────────────────────
    # Salary hard miss: candidate wants >25% above max
    salary_s = dims["salary_fit"]
    location_s = dims["location_fit"]

    hard_block = (salary_s == 0.0) or (location_s <= 0.1 and
        (job.get("remote_policy") or "").lower() not in ("remote", "hybrid"))

    # ── Decision thresholds ───────────────────────────────────────────────────
    if hard_block:
        decision = "block"
    elif overall >= 0.72:
        decision = "recommend"
    elif overall >= 0.52:
        decision = "collect_more"
    elif overall >= 0.35:
        decision = "hold"
    else:
        decision = "block"

    # ── Risk flags and narrative ──────────────────────────────────────────────
    risk_flags = _detect_risk_flags(signals, job, dims)
    why = _build_why(signals, job, dims, risk_flags, decision)

    return {
        "overall_score":  overall,
        "decision":       decision,
        "dimensions":     dims,
        "risk_flags":     risk_flags,
        "why":            why,
        "role_type":      role_type,
        "weight_profile": {d: base_weights.get(d, 0.0) for d in weighted_dims},
    }


def compatibility_decision_label(decision: str) -> str:
    return {
        "recommend":    "Send intro — strong fit",
        "collect_more": "Gather more signals before sending",
        "hold":         "Hold — borderline fit, wait for better data",
        "block":        "Do not send — fundamental mismatch",
    }.get(decision, decision)
