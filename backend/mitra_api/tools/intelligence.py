"""
mitra_api/tools/intelligence.py

Cross-side intelligence layer — makes Mitra smarter with every conversation.

Three engines:
  1. Trajectory inference  — predict where a candidate is going, not just where they are
  2. Founder pattern learn — learn each founder's real preferences from their behaviour
  3. Match confidence      — score intro confidence before sending, not after

These run as enrichment steps, not real-time blocking calls.
"""

from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)


# ── 1. CANDIDATE TRAJECTORY INFERENCE ────────────────────────────────────────

_TRAJECTORY_SYSTEM = """You are a senior talent advisor who has placed 500+ engineers at Indian startups.

Given a candidate's background and signals, infer:
1. Their career trajectory — where are they going, not just where they've been?
2. Their "type" as an engineer — what kind of environment do they actually thrive in?
3. The stage of startup they're really ready for (not what they claim)
4. What's the hidden constraint that will make or break their next move?

Return ONLY a JSON object (no markdown, no preamble):
{
  "trajectory_label": "string — 1 sentence, e.g. 'technical co-founder type in an IC role'",
  "real_stage_fit": "seed|series_a|series_b|series_c_plus",
  "hidden_constraint": "string — the thing they haven't said that will matter most",
  "engineer_type": "string — e.g. 'systems thinker who builds for scale', 'product-minded full-stack'",
  "confidence": 0.0-1.0,
  "reasoning": "string — 2-3 sentences on what led to this inference"
}

Be honest and specific. Generic inferences are useless."""


async def infer_candidate_trajectory(
    signals: dict[str, Any],
    conversation_excerpt: str = "",
) -> dict[str, Any] | None:
    """
    Infer a candidate's trajectory from their signals and conversation.
    Returns enriched trajectory data to be stored in candidate_signals.

    Called after intake completes, not during the conversation.
    Runs asynchronously so it doesn't slow down the agent turn.
    """
    from mitra_api.config import get_settings
    from mitra_api.llm.factory import get_llm_adapter
    from mitra_api.llm.types import ChatMessage

    s = get_settings()

    sig_text = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in signals.items())
    user_content = f"CANDIDATE SIGNALS:\n{sig_text}"
    if conversation_excerpt:
        user_content += f"\n\nCONVERSATION EXCERPT:\n{conversation_excerpt[:1500]}"

    try:
        adapter = get_llm_adapter(s)
        result  = await adapter.complete(
            model=s.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_TRAJECTORY_SYSTEM),
                ChatMessage(role="user",   content=user_content),
            ],
            tools=[],
            max_tokens=512,
            temperature=0.1,
        )
        raw = (result.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        trajectory = json.loads(raw)
        log.info("trajectory inferred: %s", trajectory.get("trajectory_label", "unknown"))
        return trajectory
    except Exception:
        log.exception("trajectory inference failed (non-critical)")
        return None


# ── 2. FOUNDER BEHAVIOUR LEARNING ────────────────────────────────────────────

def update_founder_response_pattern(
    existing_profile: dict[str, Any],
    *,
    responded: bool,
    response_hours: float | None,
    candidate_signals: dict[str, Any],
    passed_reason: str | None = None,
) -> dict[str, Any]:
    """
    Update a founder's behavioural profile after they respond (or don't) to an intro.

    Accumulates signals over time:
    - Response velocity
    - What candidate profiles they respond to vs pass on
    - What their stated pass reasons reveal about their real bar

    Args:
        existing_profile: Current founder profile dict (from DB or empty {})
        responded:         Did they respond at all?
        response_hours:    Hours to first response (None if no response)
        candidate_signals: The candidate's signals for this intro
        passed_reason:     If they passed, what they said

    Returns:
        Updated profile dict to be stored in DB.
    """
    profile = dict(existing_profile)

    total          = profile.get("total_intros_sent", 0) + 1
    responded_count = profile.get("total_responded", 0) + (1 if responded else 0)
    profile["total_intros_sent"] = total
    profile["total_responded"]   = responded_count
    profile["response_rate_pct"] = round(responded_count / total * 100, 1)

    if response_hours is not None and responded:
        velocities = profile.get("response_times_hours", [])
        velocities.append(round(response_hours, 1))
        velocities = velocities[-20:]
        profile["response_times_hours"] = velocities
        profile["avg_response_hours"]   = round(sum(velocities) / len(velocities), 1)

    if not responded and passed_reason:
        implicit = profile.get("implicit_filters", [])
        implicit.append({
            "reason":            passed_reason[:200],
            "candidate_stack":   candidate_signals.get("primary_stack", []),
            "candidate_yoe":     candidate_signals.get("years_experience"),
            "candidate_company": candidate_signals.get("current_company"),
        })
        profile["implicit_filters"] = implicit[-10:]

    if responded and response_hours is not None and response_hours < 12:
        fast_profiles = profile.get("fast_response_profiles", [])
        fast_profiles.append({
            "stack":   candidate_signals.get("primary_stack", []),
            "yoe":     candidate_signals.get("years_experience"),
            "company": candidate_signals.get("current_company"),
        })
        profile["fast_response_profiles"] = fast_profiles[-10:]

    return profile


# ── 3. MATCH CONFIDENCE SCORING ───────────────────────────────────────────────

def score_intro_confidence(
    candidate_signals: dict[str, Any],
    job: dict[str, Any],
    founder_profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Score the confidence of an intro before sending.

    Returns:
      - confidence: 0.0 - 1.0
      - send_recommendation: "send" | "collect_more_signals" | "hold"
      - reasons: list of strings explaining the score
      - missing_signals: list of signals that would increase confidence

    This is advisory, not a gate. Low confidence intros can still be sent.
    """
    score   = 1.0
    reasons = []
    missing = []

    # Signal completeness
    required = ["candidate_name", "primary_stack", "current_role", "motivation"]
    for key in required:
        if not candidate_signals.get(key):
            score  -= 0.10
            missing.append(key)
            reasons.append(f"Missing {key} — intro will be generic")

    # Stack match
    job_stack = set(s.lower() for s in (job.get("stack") or []))
    cand_stack_raw = candidate_signals.get("primary_stack") or []
    if isinstance(cand_stack_raw, str):
        cand_stack_raw = [cand_stack_raw]
    cand_stack = set(s.lower() for s in cand_stack_raw)

    if job_stack and not (job_stack & cand_stack):
        score  -= 0.20
        reasons.append("No stack overlap — founder may question relevance")
    elif job_stack and len(job_stack & cand_stack) >= 2:
        score  += 0.05
        reasons.append("Strong stack overlap — likely fast response")

    # Salary compatibility
    salary_target = (
        candidate_signals.get("salary_target_lpa") or
        candidate_signals.get("salary_floor_lpa")
    )
    if salary_target and job.get("salary_max_lpa"):
        try:
            if float(salary_target) > float(job["salary_max_lpa"]) * 1.1:
                score  -= 0.15
                reasons.append("Salary expectation above job max — risk of wasted conversation")
        except (TypeError, ValueError):
            pass

    # Dealbreaker check
    dealbreakers = candidate_signals.get("dealbreakers") or []
    if isinstance(dealbreakers, str):
        dealbreakers = [dealbreakers]
    job_sector  = (job.get("sector")  or "").lower()
    job_company = (job.get("company") or "").lower()
    for d in dealbreakers:
        if str(d).lower() in job_sector or str(d).lower() in job_company:
            score  -= 0.30
            reasons.append(f"Dealbreaker '{d}' matches job sector/company")

    # Founder response history
    if founder_profile:
        response_rate = founder_profile.get("response_rate_pct", 100)
        if response_rate < 30:
            score  -= 0.10
            reasons.append(f"Founder response rate is {response_rate}% — low likelihood of reply")
        elif response_rate > 70:
            score  += 0.05
            reasons.append(f"Founder is responsive ({response_rate}% reply rate)")

        for fp in founder_profile.get("fast_response_profiles", []):
            fp_stack = set(s.lower() for s in (fp.get("stack") or []))
            if fp_stack & cand_stack:
                score  += 0.05
                reasons.append("Candidate stack matches profiles this founder responded to quickly")
                break

    score = max(0.0, min(1.0, score))

    if score >= 0.75:
        recommendation = "send"
    elif score >= 0.50:
        recommendation = "collect_more_signals"
    else:
        recommendation = "hold"

    return {
        "confidence":          round(score, 2),
        "send_recommendation": recommendation,
        "reasons":             reasons,
        "missing_signals":     missing,
    }


# ── 4. CONVERSATION QUALITY SCORER ───────────────────────────────────────────

def score_conversation_quality(signals: dict[str, Any]) -> dict[str, Any]:
    """
    Score a candidate intake conversation for signal completeness.
    Returns a score and what's still needed.

    Used by the orchestrator to inject a readiness hint into the agent turn.
    """
    weights = {
        "motivation":         25,
        "primary_stack":      20,
        "salary_floor_lpa":   15,
        "location_preference":10,
        "startup_stage_pref": 10,
        "current_role":        8,
        "notice_period_days":  7,
        "dealbreakers":        5,
    }

    score   = 0
    missing = []
    present = []

    for key, weight in weights.items():
        if signals.get(key):
            score += weight
            present.append(key)
        else:
            missing.append({"key": key, "weight": weight})

    missing.sort(key=lambda x: x["weight"], reverse=True)

    if score >= 80:
        readiness = "match_ready"
        next_step = "search_jobs"
    elif score >= 55:
        readiness = "almost_ready"
        next_step = missing[0]["key"] if missing else "search_jobs"
    else:
        readiness = "needs_more"
        next_step = missing[0]["key"] if missing else "search_jobs"

    return {
        "score":       score,
        "readiness":   readiness,
        "next_step":   next_step,
        "present":     present,
        "missing":     [m["key"] for m in missing],
        "top_missing": missing[0]["key"] if missing else None,
    }
