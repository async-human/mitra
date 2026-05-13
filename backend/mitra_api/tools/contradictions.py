"""
mitra_api/tools/contradictions.py

Rule-based contradiction detection — detects when a candidate's stated
preference contradicts revealed behavior or other stated signals.

Pure functions, no DB or LLM required. Runs synchronously in the orchestrator
each turn (cheap: ~1ms). The Layer B LLM check is a separate module that runs
less often.

Design principles
-----------------
- Conservative. Below confidence 0.6 → drop. Prefer false negatives.
- Evidence-bound. Every contradiction carries a quote/paraphrase of both sides.
- Single-dimension. One contradiction = one dimension. No multi-axis blobs.
- Probe-aware. The orchestrator marks a dimension as probed once it's been
  surfaced to the agent, so the same tension doesn't get raised every turn.

Public API
----------
detect_contradictions(signals)          -> list[dict]
merge_contradictions(existing, new)     -> list[dict]
select_tension_to_probe(c, probed)      -> dict | None
build_contradictions_context_injection(c, probed) -> tuple[str, str | None]
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Literal

log = logging.getLogger(__name__)

# Below this confidence, drop the contradiction entirely.
_MIN_CONFIDENCE = 0.6

# Salary thresholds (LPA, Indian startup context).
_HIGH_SALARY_TARGET = 80

# Stage keyword sets — matched against startup_stage_pref / open_to.
_EARLY_STAGE_TOKENS = (
    "seed", "pre-seed", "preseed", "founding", "early-stage", "early stage",
)
_LATE_STAGE_TOKENS = (
    "series b", "series c", "growth", "late-stage", "late stage", "public",
)


@dataclass
class Contradiction:
    dimension: str
    stated: str
    revealed: str
    confidence: float
    severity: Literal["soft", "hard"]
    suggested_probe: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalize_str_list(value: Any) -> list[str]:
    """Coerce a signal value (str | list | None) into a lowercased list."""
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip().lower() for v in value.split(",") if v.strip()]
    if isinstance(value, list):
        return [str(v).strip().lower() for v in value if v]
    return []


def _contains_any(haystack: str, tokens: Iterable[str]) -> bool:
    h = (haystack or "").lower()
    return any(t in h for t in tokens)


def _list_contains_any(values: list[str], tokens: Iterable[str]) -> bool:
    return any(any(t in v for t in tokens) for v in values)


def _list_contains_only(values: list[str], tokens: Iterable[str]) -> bool:
    """All values match at least one of the tokens. False on empty list."""
    if not values:
        return False
    return all(any(t in v for t in tokens) for v in values)


# ── Rules ──────────────────────────────────────────────────────────────────────

def _check_ownership_vs_stage(signals: dict[str, Any]) -> Contradiction | None:
    """Wants ownership / 0→1 energy, but only open to late-stage companies."""
    pull       = (signals.get("career_pull") or "").lower()
    motivation = (signals.get("motivation")  or "").lower()
    ownership  = (signals.get("ownership_level") or "").lower()

    wants_ownership = (
        ownership == "high"
        or _contains_any(pull, ("ownership", "founding", "build from scratch", "0 to 1", "0->1"))
        or _contains_any(motivation, ("ownership", "founding"))
    )

    stage_pref = _normalize_str_list(signals.get("startup_stage_pref"))
    if not stage_pref:
        return None

    only_late = _list_contains_only(stage_pref, _LATE_STAGE_TOKENS)
    no_early  = not _list_contains_any(stage_pref, _EARLY_STAGE_TOKENS)

    if not (wants_ownership and (only_late or no_early)):
        return None

    return Contradiction(
        dimension="ownership_vs_stage",
        stated="wants ownership / build-from-scratch energy",
        revealed=f"prefers later-stage companies: {', '.join(stage_pref)}",
        confidence=0.75 if only_late else 0.65,
        severity="hard" if only_late else "soft",
        suggested_probe=(
            "What level of build-from-scratch energy do you actually want? "
            "Real ownership tends to live at seed / Series A — Series B+ is "
            "usually owning a slice, not the whole thing."
        ),
    )


def _check_salary_vs_stage(signals: dict[str, Any]) -> Contradiction | None:
    """High salary target, but open to seed / founding roles (where cash is lower)."""
    target_raw = signals.get("salary_target_lpa") or signals.get("salary_floor_lpa")
    try:
        target = float(target_raw) if target_raw is not None else None
    except (TypeError, ValueError):
        target = None
    if target is None or target < _HIGH_SALARY_TARGET:
        return None

    stage_pref = _normalize_str_list(signals.get("startup_stage_pref"))
    open_to    = _normalize_str_list(signals.get("open_to"))
    early_signals = (
        _list_contains_any(stage_pref, _EARLY_STAGE_TOKENS)
        or _list_contains_any(open_to, _EARLY_STAGE_TOKENS)
    )
    if not early_signals:
        return None

    return Contradiction(
        dimension="salary_vs_stage",
        stated=f"target salary ~₹{int(target)} LPA",
        revealed="open to seed / founding roles where cash comp is typically 30-50% lower",
        confidence=0.8,
        severity="hard",
        suggested_probe=(
            "Cash and seed-stage usually trade off — equity makes up the difference. "
            "If you had to pick between higher cash at Series B or more equity at seed, "
            "which way do you lean?"
        ),
    )


def _check_risk_vs_stability(signals: dict[str, Any]) -> Contradiction | None:
    """Wants high-growth / high-risk, but has financial pressure or stability signals."""
    risk = (signals.get("risk_tolerance") or "").lower()
    pull = (signals.get("career_pull")    or "").lower()
    push = (signals.get("career_push")    or "").lower()

    wants_risk = (
        risk == "high"
        or _contains_any(pull, ("high-risk", "high risk", "high growth", "high-growth"))
    )
    needs_stability = (
        signals.get("financial_pressure") is True
        or _contains_any(push, ("stability", "stable income", "secure"))
    )

    if not (wants_risk and needs_stability):
        return None

    revealed = (
        "financial pressure / dependents mentioned"
        if signals.get("financial_pressure") is True
        else "earlier mentioned needing stability"
    )

    return Contradiction(
        dimension="risk_vs_stability",
        stated="wants high-growth / high-risk environment",
        revealed=revealed,
        confidence=0.7,
        severity="soft",
        suggested_probe=(
            "What does the right level of financial cushion look like? "
            "Funded Series A is usually the sweet spot for high-growth + reasonable security."
        ),
    )


def _check_urgency_vs_flexibility(signals: dict[str, Any]) -> Contradiction | None:
    """Stated urgency 'high', but notice period is long or fixed."""
    urgency = (signals.get("urgency") or "").lower()
    if urgency not in ("high", "very_high"):
        return None

    notice = signals.get("notice_period_days")
    flex   = (signals.get("notice_period_flexibility") or "").lower()

    has_long_notice = isinstance(notice, (int, float)) and notice >= 60
    is_fixed = flex == "fixed"

    if not (has_long_notice or is_fixed):
        return None

    revealed_parts: list[str] = []
    if has_long_notice:
        revealed_parts.append(f"{int(notice)}-day notice period")
    if is_fixed:
        revealed_parts.append("notice is fixed / non-negotiable")

    return Contradiction(
        dimension="urgency_vs_flexibility",
        stated="wants to move urgently",
        revealed=" + ".join(revealed_parts),
        confidence=0.7,
        severity="soft",
        suggested_probe=(
            "Realistically, when's the earliest you could start? "
            "I want to target roles that fit your actual timeline."
        ),
    )


def _check_pace_vs_clarity(signals: dict[str, Any]) -> Contradiction | None:
    """Wants fast-moving environment, but avoids ambiguity / unclear scope."""
    pull = (signals.get("career_pull") or "").lower()
    push = (signals.get("career_push") or "").lower()
    dealbreakers = _normalize_str_list(signals.get("dealbreaker_signals"))

    wants_pace = _contains_any(
        pull, ("fast-moving", "fast moving", "high-pace", "high pace", "speed", "velocity")
    )
    avoids_ambiguity = (
        _contains_any(push, ("ambiguity", "unclear scope", "chaos", "no direction"))
        or _list_contains_any(dealbreakers, ("ambiguity", "chaos", "unclear"))
    )

    if not (wants_pace and avoids_ambiguity):
        return None

    return Contradiction(
        dimension="pace_vs_clarity",
        stated="wants a fast-moving environment",
        revealed="avoids ambiguity / unclear scope",
        confidence=0.65,
        severity="soft",
        suggested_probe=(
            "When you say fast-moving — clear roadmaps shipped quickly, or "
            "more 'figure it out as we go'? Those are very different teams."
        ),
    )


def _check_remote_vs_collaboration(signals: dict[str, Any]) -> Contradiction | None:
    """Remote-only preference, but values mentorship / strong team culture."""
    prefs = _normalize_str_list(signals.get("location_preference"))
    only_remote = bool(prefs) and all("remote" in p for p in prefs)
    if not only_remote:
        return None

    pull       = (signals.get("career_pull") or "").lower()
    motivation = (signals.get("motivation")  or "").lower()
    wants_team = (
        _contains_any(pull, ("mentorship", "mentor", "learning from", "team culture", "strong team"))
        or _contains_any(motivation, ("mentorship", "team culture"))
    )
    if not wants_team:
        return None

    return Contradiction(
        dimension="remote_vs_collaboration",
        stated="remote-only preference",
        revealed="values mentorship / strong team culture",
        confidence=0.6,
        severity="soft",
        suggested_probe=(
            "Remote-only and 'strong mentorship' can be hard to combine at early-stage "
            "startups. Open to hybrid (2-3 days) if the team is exceptional?"
        ),
    )


_RULES = (
    _check_ownership_vs_stage,
    _check_salary_vs_stage,
    _check_risk_vs_stability,
    _check_urgency_vs_flexibility,
    _check_pace_vs_clarity,
    _check_remote_vs_collaboration,
)


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_contradictions(signals: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Run all rule-based contradiction checks. Returns serializable dicts ready
    to merge into signals under `_implicit_contradictions`.

    Conservative by design — returns [] when in doubt.
    """
    out: list[dict[str, Any]] = []
    for rule in _RULES:
        try:
            result = rule(signals)
        except Exception:
            log.debug("contradiction rule %s failed", rule.__name__, exc_info=True)
            continue
        if result and result.confidence >= _MIN_CONFIDENCE:
            out.append(result.to_dict())
    return out


def merge_contradictions(
    existing: list[dict[str, Any]] | None,
    new: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge newly-detected contradictions into the existing list, deduplicating
    by `dimension`. Higher confidence wins on conflict.
    """
    by_dim: dict[str, dict[str, Any]] = {}
    for c in (existing or []):
        if isinstance(c, dict) and "dimension" in c:
            by_dim[c["dimension"]] = c
    for c in new:
        dim = c.get("dimension")
        if not dim:
            continue
        prev = by_dim.get(dim)
        if prev is None or float(c.get("confidence", 0)) >= float(prev.get("confidence", 0)):
            by_dim[dim] = c
    return list(by_dim.values())


def select_tension_to_probe(
    contradictions: list[dict[str, Any]] | None,
    probed_dimensions: list[str] | None,
) -> dict[str, Any] | None:
    """
    Pick the single most important tension to surface this turn:
    - skip already-probed dimensions
    - prefer hard severity over soft
    - within severity, prefer higher confidence
    """
    if not contradictions:
        return None
    probed = set(probed_dimensions or [])
    pool = [c for c in contradictions if c.get("dimension") not in probed]
    if not pool:
        return None

    def sort_key(c: dict[str, Any]) -> tuple[int, float]:
        sev_rank = 1 if c.get("severity") == "hard" else 0
        return (sev_rank, float(c.get("confidence", 0)))

    return max(pool, key=sort_key)


def build_contradictions_context_injection(
    contradictions: list[dict[str, Any]] | None,
    probed_dimensions: list[str] | None,
) -> tuple[str, str | None]:
    """
    Build the [CANDIDATE INTERNAL TENSION] injection block for the agent.

    Returns (block_text, selected_dimension_or_None). The orchestrator marks
    `selected_dimension` as probed in signals so the same tension is not
    raised on subsequent turns.

    Returns ("", None) when there is nothing to probe.
    """
    selected = select_tension_to_probe(contradictions, probed_dimensions)
    if not selected:
        return "", None

    block = (
        "[CANDIDATE INTERNAL TENSION — gentle probe, do not accuse]\n"
        f"- Dimension: {selected['dimension']}\n"
        f"- Stated: {selected['stated']}\n"
        f"- Observed: {selected['revealed']}\n"
        f"- Severity: {selected['severity']} "
        f"(confidence {float(selected.get('confidence', 0)):.2f})\n"
        f"- Suggested probe: {selected['suggested_probe']}\n"
        "Use this as a hint, not a script. Reference it naturally and curiously — "
        "phrase as a question that lets them clarify their own thinking. "
        "Never repeat the suggested probe verbatim. Probe at most once per turn."
    )
    return block, selected["dimension"]
