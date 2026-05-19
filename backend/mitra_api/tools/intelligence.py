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

# Valid structured pass-reason codes — used by the founder portal and analytics.
# Free text (decline_reason) is still captured alongside for nuance.
PASS_REASON_CODES: dict[str, str] = {
    "skill_gap":          "Tech stack doesn't match the role",
    "seniority_mismatch": "Too junior or too senior",
    "salary_mismatch":    "Salary expectations too high",
    "notice_too_long":    "Notice period is too long",
    "ownership_lacking":  "Insufficient ownership track record",
    "culture_fit":        "Culture or values misalignment",
    "timing":             "Role paused or not hiring right now",
    "other":              "Other reason",
}


def update_founder_response_pattern(
    existing_profile: dict[str, Any],
    *,
    responded: bool,
    response_hours: float | None,
    candidate_signals: dict[str, Any],
    passed_reason: str | None = None,
    passed_reason_code: str | None = None,
) -> dict[str, Any]:
    """
    Update a founder's behavioural profile after they respond (or don't) to an intro.

    Accumulates over time:
    - Response velocity (how fast they reply)
    - Pass-reason code frequency (their real bar, machine-readable)
    - Candidate profiles they respond to vs pass on (stack, YoE, company)
    - Fast-response profiles (who excites them within 12h)
    """
    profile = dict(existing_profile)

    total           = profile.get("total_intros_sent", 0) + 1
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

    if not responded:
        # Track structured code frequency — e.g. {"skill_gap": 3, "salary_mismatch": 1}
        if passed_reason_code and passed_reason_code in PASS_REASON_CODES:
            freq = dict(profile.get("pass_reason_freq", {}))
            freq[passed_reason_code] = freq.get(passed_reason_code, 0) + 1
            profile["pass_reason_freq"] = freq

            # Surface the top rejection pattern for the agent's context injection
            top_code = max(freq, key=lambda k: freq[k])
            profile["top_pass_reason"] = {
                "code":  top_code,
                "label": PASS_REASON_CODES[top_code],
                "count": freq[top_code],
            }

        if passed_reason:
            implicit = profile.get("implicit_filters", [])
            implicit.append({
                "reason":            passed_reason[:200],
                "reason_code":       passed_reason_code,
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


# ── 3b. OUTCOME LEARNING (Phase 5) ───────────────────────────────────────────

async def learn_from_outcome(
    intro_id: int,
    outcome: str,
    decline_reason_code: str | None,
    session: Any,
) -> None:
    """
    Learn from a founder's response to an intro.

    - accepted / interview / offer / hired → reinforce high-scoring dimensions
    - declined with reason → record which dimensions predicted the decline
    - ghost (no reply after N days) → reduce founder trust_score

    Results are stored as agent_memory_snapshots for future calibration.
    Updates job.founder_profile with the latest trust_score.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select

    try:
        from mitra_api.db.models import Intro, Match, Job, CandidateSignal

        intro: Any = (await session.execute(
            select(Intro).where(Intro.id == intro_id)
        )).scalar_one_or_none()
        if not intro:
            log.warning("learn_from_outcome: intro %d not found", intro_id)
            return

        job: Any = (await session.execute(
            select(Job).where(Job.id == intro.job_id)
        )).scalar_one_or_none()
        if not job:
            return

        # Load the match record to get stored compatibility dimensions
        match: Any = (await session.execute(
            select(Match).where(Match.intro_id == intro_id)
        )).scalar_one_or_none()

        compat_dims: dict[str, Any] = {}
        if match and match.compatibility_dimensions:
            compat_dims = match.compatibility_dimensions

        # Load candidate signals
        sig_rows = (await session.execute(
            select(CandidateSignal).where(CandidateSignal.candidate_id == intro.candidate_id)
        )).scalars().all()
        candidate_signals: dict[str, Any] = {r.key: r.value for r in sig_rows}

        # ── Update founder trust score ────────────────────────────────────────
        fp = job.founder_profile or (
            job.signals.get("_founder_profile", {}) if isinstance(job.signals, dict) else {}
        )
        fp = dict(fp)

        positive = outcome in ("interested", "interview", "offer", "hired")
        ghost = outcome == "ghosted"

        total = fp.get("total_intros", 0) + 1
        fp["total_intros"] = total
        if positive:
            fp["total_responses"] = fp.get("total_responses", 0) + 1
        response_rate = fp.get("total_responses", 0) / max(total, 1)
        fp["response_rate"] = round(response_rate, 3)

        # Trust score: weighted toward recent behavior
        current_trust = fp.get("trust_score", 0.5)
        if positive:
            fp["trust_score"] = round(min(1.0, current_trust * 0.85 + 0.15), 3)
        elif ghost:
            fp["trust_score"] = round(max(0.1, current_trust * 0.90), 3)
        else:
            # Declined with reason — neutral impact
            fp["trust_score"] = round(max(0.2, current_trust * 0.95), 3)

        fp["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Persist updated profile
        job.founder_profile = fp

        # ── Snapshot outcome for learning (Phase 5 dataset) ──────────────────
        try:
            from sqlalchemy import text
            payload: dict[str, Any] = {
                "outcome":            outcome,
                "decline_reason_code": decline_reason_code,
                "compat_dims":        compat_dims,
                "candidate_signals":  {
                    k: v for k, v in candidate_signals.items()
                    if k in ("primary_stack", "years_experience", "salary_floor_lpa",
                             "ownership_mindset", "motivation", "location_preference",
                             "risk_tolerance", "startup_stage_pref")
                },
                "trust_score_after":  fp["trust_score"],
                "job_stage":          job.stage,
                "job_sector":         job.sector,
            }
            await session.execute(
                text("""
                    INSERT INTO agent_memory_snapshots
                        (subject_type, subject_id, memory_type, payload, policy_version)
                    VALUES (:st, :sid, :mt, :pl::jsonb, :pv)
                """),
                {
                    "st": "founder",
                    "sid": job.id,
                    "mt": "outcome_signal",
                    "pl": json.dumps(payload),
                    "pv": "v1",
                },
            )
        except Exception:
            log.debug("learn_from_outcome: snapshot insert failed (non-critical)")

        await session.flush()
        log.info(
            "learn_from_outcome: intro=%d outcome=%s trust=%.2f",
            intro_id, outcome, fp["trust_score"],
        )
    except Exception:
        log.exception("learn_from_outcome failed for intro=%d", intro_id)


# ── 4. POST-TURN REFLECTION ───────────────────────────────────────────────────

_REFLECTION_SYSTEM = """You are an internal analyst for an AI talent agent.

After each candidate interaction, generate a compact behavioral delta.

Return ONLY a JSON object (no markdown, no explanation):
{
  "behavioral_shift": "string or null — what changed in tone/urgency/openness this turn. Be specific.",
  "hypothesis_update": "string or null — what this turn confirms or weakens about their trajectory",
  "emotional_tone": "curious|enthusiastic|anxious|guarded|decisive|distracted|frustrated",
  "phase": "exploring|active_search|interviewing|negotiating|placed",
  "remember": "string or null — single most important new thing to carry forward"
}

Rules:
- Be specific. "Seems interested" is useless. Name the exact signal.
- If nothing changed, return null for that field. Don't fill fields with noise.
- Phase: exploring=browsing options, active_search=ready to interview now,
  interviewing=in process with a company, negotiating=has an offer, placed=accepted."""


async def generate_turn_reflection(
    user_message: str,
    known_signals: dict[str, Any],
    assistant_response: str,
) -> dict[str, Any] | None:
    """
    Generate a behavioral delta after one agent turn.

    Runs as a fire-and-forget background task — never blocks the agent response.
    Result is persisted as _reflection and injected on the NEXT turn.
    """
    if not user_message.strip():
        return None

    from mitra_api.config import get_settings
    from mitra_api.llm.factory import get_llm_adapter
    from mitra_api.llm.types import ChatMessage

    s = get_settings()

    sig_summary = json.dumps(
        {k: v for k, v in known_signals.items() if not k.startswith("_")},
        ensure_ascii=False,
    )
    user_content = (
        f"USER_MESSAGE:\n{user_message[:800]}\n\n"
        f"KNOWN_SIGNALS:\n{sig_summary[:600]}\n\n"
        f"ASSISTANT_RESPONSE:\n{assistant_response[:400]}"
    )

    try:
        adapter = get_llm_adapter(s)
        result = await adapter.complete(
            model=s.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_REFLECTION_SYSTEM),
                ChatMessage(role="user",   content=user_content),
            ],
            tools=[],
            max_tokens=256,
            temperature=0.1,
        )
        raw = (result.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        reflection = json.loads(raw)
        log.info(
            "reflection: phase=%s tone=%s shift=%s",
            reflection.get("phase"), reflection.get("emotional_tone"),
            bool(reflection.get("behavioral_shift")),
        )
        return reflection
    except Exception:
        log.debug("turn reflection failed (non-critical)")
        return None


# ── 5. CONVERSATION QUALITY SCORER ───────────────────────────────────────────

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
