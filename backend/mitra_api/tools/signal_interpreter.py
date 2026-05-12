"""
mitra_api/tools/signal_interpreter.py

Signal interpretation engine — turns raw candidate/founder messages into
structured intelligence the agent can act on immediately.

Two layers:
  1. Rule-based extractors (synchronous, zero latency, free)
     salary_mention, timing_signals, hesitation_signals, ownership_signals
     Run before every LLM call; results merged into session signals instantly.

  2. Deep LLM interpreter (async background task, Claude Haiku)
     Interprets the full conversational context for implicit signals.
     Result stored as _last_interpretation and injected into the NEXT turn.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

log = logging.getLogger(__name__)


# ── CANDIDATE DEEP INTERPRETER ────────────────────────────────────────────────

_CANDIDATE_INTERPRETER_SYSTEM = """\
You are a senior talent psychologist and career advisor with 15 years of
experience placing engineers at Indian startups.

Given a fragment of a candidate's WhatsApp conversation with a talent agent,
extract every meaningful signal — including the ones that aren't explicitly stated.
Your job is to interpret, not just transcribe.

Signal categories to look for:

MOTIVATIONAL — why they're really moving (often different from what they say),
urgency level, push factors (escaping) vs pull factors (toward), emotional state.

CAREER TRAJECTORY — actual vs stated seniority, ownership vs execution mindset,
builder vs maintainer personality, first startup move vs experienced.

CONSTRAINT — hidden dealbreakers, financial pressure, risk tolerance (do they
mention stability? safety? EMI?).

TRUST & ENGAGEMENT — how candid are they? Do they give polished or real answers?
What topics do they avoid?

QUALITY — genuine ownership vs participation, specific technical detail vs vague
claims, impact orientation vs task orientation.

TIMING — competing offers, financial events (bonus cliff, ESOP vesting, appraisal),
how long they've been thinking about this.

Return a JSON object:
{
  "signals": [
    {
      "signal_key": "real_motivation",
      "raw_value": "I want to grow and work on impactful products",
      "interpreted_value": "Standard non-answer. Real motivation is likely push-driven.",
      "confidence": 0.7,
      "agent_implication": "Probe: what changed recently? Don't accept polished answer."
    }
  ],
  "overall_read": "2-3 sentence synthesis of who this person is and what they need",
  "immediate_next_question": "The single most important question to ask next",
  "red_flags": ["list of things to watch for"],
  "green_flags": ["list of genuinely positive signals"]
}

Be specific. Generic interpretations are worthless.
Reply with ONLY the JSON object — no markdown fence, no explanation."""


_FOUNDER_INTERPRETER_SYSTEM = """\
You are a senior executive recruiter who has placed engineering leaders at
100+ funded startups in India.

Given a fragment of a founder's onboarding conversation, extract every meaningful
signal — especially the gap between stated and real hiring need.

Signal categories:
REAL REQUIREMENT — gap between what they say they need and the underlying business
problem, whether the role is well-defined or exploratory, signs of previous bad hires.

CULTURE — what the engineering culture actually is (revealed in passing), power
dynamics, pace expectations, whether they value craft vs speed vs impact.

URGENCY & COMMITMENT — is this a real open role? Pain level, decision-making speed,
whether headcount and budget actually exist.

EXPECTATION CALIBRATION — is salary range realistic? Experience requirements aligned
with what they can offer? Signs of wishful thinking.

TRUST — how candid are they about challenges? Do they describe hard parts or only
the exciting ones?

Return the same JSON structure. Be specific.
Reply with ONLY the JSON object — no markdown fence, no explanation."""


async def interpret_candidate_message(
    message: str,
    conversation_history: list[dict[str, str]],
    existing_signals: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Deep-interpret a candidate's message using Claude Haiku.

    Called as a background task — result stored for next turn, not this one.
    conversation_history should be a snapshot (list of role/content dicts),
    NOT a live reference to the msgs list.
    """
    from mitra_api.config import get_settings
    import httpx

    s = get_settings()
    api_key = s.anthropic_api_key.strip()
    if not api_key:
        return None

    history_text = "\n".join(
        f"{m.get('role', 'unknown').upper()}: {m.get('content', '')}"
        for m in conversation_history[-6:]
    )
    existing_text = json.dumps(
        {k: v for k, v in existing_signals.items() if not k.startswith("_")},
        ensure_ascii=False,
        indent=2,
    ) if existing_signals else "{}"

    user_content = (
        f"EXISTING SIGNALS:\n{existing_text}\n\n"
        f"RECENT CONVERSATION:\n{history_text}\n\n"
        f"LATEST CANDIDATE MESSAGE:\n{message}\n\n"
        f"Interpret this. What does it really mean? What should the agent do next?"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json={
                    "model":       "claude-haiku-4-5-20251001",
                    "max_tokens":  1024,
                    "temperature": 0.1,
                    "system":      _CANDIDATE_INTERPRETER_SYSTEM,
                    "messages":    [{"role": "user", "content": user_content}],
                },
                headers={
                    "x-api-key":         api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
            )
            resp.raise_for_status()
            raw = resp.json()["content"][0]["text"].strip()
            # Strip optional markdown fence
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json\n").strip()
            result = json.loads(raw)
            log.debug(
                "candidate interpretation complete: %d signals, read=%.60r",
                len(result.get("signals", [])),
                result.get("overall_read", ""),
            )
            return result
    except Exception:
        log.debug("candidate message interpretation failed (non-critical)", exc_info=True)
        return None


async def interpret_founder_message(
    message: str,
    conversation_history: list[dict[str, str]],
    existing_signals: dict[str, Any],
) -> dict[str, Any] | None:
    """Deep-interpret a founder's message using Claude Haiku."""
    from mitra_api.config import get_settings
    import httpx

    s = get_settings()
    api_key = s.anthropic_api_key.strip()
    if not api_key:
        return None

    history_text = "\n".join(
        f"{m.get('role', 'unknown').upper()}: {m.get('content', '')}"
        for m in conversation_history[-6:]
    )
    existing_text = json.dumps(
        {k: v for k, v in existing_signals.items() if not k.startswith("_")},
        ensure_ascii=False,
        indent=2,
    ) if existing_signals else "{}"

    user_content = (
        f"EXISTING SIGNALS:\n{existing_text}\n\n"
        f"RECENT CONVERSATION:\n{history_text}\n\n"
        f"LATEST FOUNDER MESSAGE:\n{message}\n\n"
        f"Interpret this. What does it really mean about their real hiring need?"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json={
                    "model":       "claude-haiku-4-5-20251001",
                    "max_tokens":  1024,
                    "temperature": 0.1,
                    "system":      _FOUNDER_INTERPRETER_SYSTEM,
                    "messages":    [{"role": "user", "content": user_content}],
                },
                headers={
                    "x-api-key":         api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
            )
            resp.raise_for_status()
            raw = resp.json()["content"][0]["text"].strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json\n").strip()
            return json.loads(raw)
    except Exception:
        log.debug("founder message interpretation failed (non-critical)", exc_info=True)
        return None


# ── SIGNAL EXTRACTION HELPERS ─────────────────────────────────────────────────

def extract_implicit_signals(interpretation: dict[str, Any]) -> dict[str, Any]:
    """
    Convert interpretation output into storable signals (confidence ≥ 0.65 only).
    Prefixed with _implicit_ to distinguish from stated signals.
    """
    if not interpretation:
        return {}

    implicit: dict[str, Any] = {}
    for sig in interpretation.get("signals", []):
        confidence = float(sig.get("confidence", 0))
        if confidence < 0.65:
            continue
        key = sig.get("signal_key", "")
        val = sig.get("interpreted_value") or sig.get("raw_value", "")
        if key and val:
            implicit[f"_implicit_{key}"] = {
                "value":       val,
                "raw":         sig.get("raw_value", ""),
                "confidence":  confidence,
                "implication": sig.get("agent_implication", ""),
            }

    if interpretation.get("overall_read"):
        implicit["_overall_read"] = interpretation["overall_read"]
    if interpretation.get("red_flags"):
        implicit["_red_flags"] = interpretation["red_flags"]
    if interpretation.get("green_flags"):
        implicit["_green_flags"] = interpretation["green_flags"]

    return implicit


def build_interpretation_context_injection(
    interpretation: dict[str, Any] | None,
) -> str:
    """
    Format last turn's interpretation as a [SIGNAL INTELLIGENCE: ...] block.

    Injected as a system message so the agent sees it without it appearing in
    the transcript or the raw signals JSON dump.
    """
    if not interpretation:
        return ""

    parts: list[str] = []

    overall = (interpretation.get("overall_read") or "").strip()
    if overall:
        parts.append(overall)

    next_q = (interpretation.get("immediate_next_question") or "").strip()
    if next_q:
        parts.append(f"Priority next question: {next_q}")

    red_flags = interpretation.get("red_flags") or []
    if red_flags:
        parts.append(f"Watch for: {'; '.join(str(f) for f in red_flags[:2])}")

    green_flags = interpretation.get("green_flags") or []
    if green_flags:
        parts.append(f"Strong signals: {'; '.join(str(f) for f in green_flags[:2])}")

    # Surface the highest-confidence implication
    best_sig = max(
        (s for s in interpretation.get("signals", []) if s.get("agent_implication")),
        key=lambda s: float(s.get("confidence", 0)),
        default=None,
    )
    if best_sig and float(best_sig.get("confidence", 0)) >= 0.80:
        parts.append(best_sig["agent_implication"])

    if not parts:
        return ""

    return "[SIGNAL INTELLIGENCE: " + " | ".join(parts) + "]"


# ── RULE-BASED EXTRACTORS ─────────────────────────────────────────────────────

def interpret_salary_mention(
    raw_text: str,
    existing_signals: dict[str, Any],
) -> dict[str, Any]:
    """
    Extract salary signals from natural language. Handles LPA / in-hand / ranges.
    Returns only keys that are genuinely new or more specific than what's stored.
    """
    text = raw_text.lower()
    sigs: dict[str, Any] = {}

    number_pattern = r'(\d+(?:\.\d+)?)\s*(?:l|lpa|lakh|lakhs|lac|lacs)?'
    numbers = [float(m.group(1)) for m in re.finditer(number_pattern, text)
               if float(m.group(1)) >= 5]  # ignore small numbers (years, %, etc.)

    if not numbers:
        return sigs

    in_hand = "in hand" in text or "in-hand" in text or "take home" in text
    multiply = 1.3 if in_hand else 1.0

    if any(kw in text for kw in ["currently", "current ctc", "earning", "drawing", "getting", "at present"]):
        sigs["current_ctc_lpa"] = round(numbers[0] * multiply, 1)

    if any(kw in text for kw in ["at least", "minimum", "won't go below", "not less than", "floor"]):
        sigs["salary_floor_lpa"] = round(max(numbers) * multiply, 1)

    if len(numbers) >= 2 and any(kw in text for kw in ["between", "range", "-", "to "]):
        lo, hi = sorted(numbers[:2])
        sigs["salary_min_lpa"]    = round(lo * multiply, 1)
        sigs["salary_max_lpa"]    = round(hi * multiply, 1)
        sigs["salary_target_lpa"] = round((lo + hi) / 2 * multiply, 1)
    elif len(numbers) == 1 and not sigs:
        if any(kw in text for kw in ["looking for", "expecting", "want", "target", "hoping"]):
            sigs["salary_target_lpa"] = round(numbers[0] * multiply, 1)

    if in_hand and sigs:
        sigs["_salary_note"] = "Quoted in-hand figure — converted to approx CTC (×1.3)"

    return sigs


def interpret_timing_signals(text: str) -> dict[str, Any]:
    """Extract urgency and timing signals."""
    lower = text.lower()
    sigs: dict[str, Any] = {}

    if any(kw in lower for kw in [
        "already interviewing", "have interviews", "talking to other",
        "in process at", "final round", "offer in hand", "got an offer",
        "received offer", "offer from",
    ]):
        sigs["actively_interviewing"] = True
        sigs["urgency"] = "high"
        sigs["framing_hint"] = (
            "Candidate is actively interviewing elsewhere. Move fast — "
            "acknowledge the timeline, search immediately, don't linger on intake."
        )

    deadline_patterns = [
        r"deadline (?:is |in )?(\d+) (?:days?|weeks?)",
        r"offer (?:expires?|valid) (?:for )?(\d+) (?:days?|weeks?)",
        r"need to decide (?:by|in) (\d+)",
        r"(\d+) days? to decide",
    ]
    for pattern in deadline_patterns:
        m = re.search(pattern, lower)
        if m:
            sigs["offer_deadline_hint"] = m.group(0)
            sigs["urgency"] = "very_high"
            sigs["framing_hint"] = (
                f"URGENT — candidate has an offer deadline ({m.group(0)}). "
                "Skip intake. Search immediately. Acknowledge the deadline first."
            )
            break

    notice_patterns = [
        r"(\d+)\s*(?:day|month|week)s?\s*notice",
        r"notice\s*(?:period\s*)?(?:is\s*)?(\d+)",
        r"can (?:join|start) in (\d+)\s*(?:day|month|week)",
    ]
    for pattern in notice_patterns:
        m = re.search(pattern, lower)
        if m:
            val = int(m.group(1))
            if "month" in m.group(0):
                val *= 30
            elif "week" in m.group(0):
                val *= 7
            sigs["notice_period_days"] = val
            break

    if any(kw in lower for kw in [
        "just exploring", "not actively", "keeping options open",
        "no rush", "not urgent", "whenever something good comes",
    ]):
        sigs["actively_looking"] = False
        if "urgency" not in sigs:
            sigs["urgency"] = "low"
    elif any(kw in lower for kw in [
        "actively looking", "need to move", "want to leave",
        "ready to move", "want to switch soon", "looking to move",
    ]):
        sigs["actively_looking"] = True
        if "urgency" not in sigs:
            sigs["urgency"] = "medium"

    if any(kw in lower for kw in [
        "bonus in", "appraisal", "esop vesting", "equity vesting",
        "increment", "joining bonus",
    ]):
        sigs["financial_event_hint"] = True

    return sigs


def interpret_hesitation_signals(text: str) -> dict[str, Any]:
    """Detect risk aversion, first-startup-move anxiety, imposter syndrome."""
    lower = text.lower()
    sigs: dict[str, Any] = {}

    stability_kws = [
        "stable", "stability", "job security", "layoffs", "safe",
        "established", "not a risk taker", "family responsibilities",
        "emi", "home loan", "mortgage",
    ]
    if sum(1 for kw in stability_kws if kw in lower) >= 2:
        sigs["risk_appetite"]     = "low"
        sigs["stability_seeking"] = True
        sigs["framing_hint"]      = "Emphasise funded status, runway, team strength — not equity upside"

    first_move_kws = [
        "never worked at a startup", "always been at", "big company background",
        "nervous about startup", "worried about startup", "scared of startup",
        "my first startup", "not sure about startup life",
    ]
    if any(kw in lower for kw in first_move_kws):
        sigs["first_startup_move"] = True
        sigs["needs_reassurance"]  = True
        sigs["framing_hint"]       = "Address MNC-to-startup transition directly before presenting roles"

    imposter_kws = [
        "not sure if i'm good enough", "maybe i'm overreaching",
        "perhaps i'm asking too much", "is that realistic",
        "don't know if i qualify", "might be out of my league",
    ]
    if any(kw in lower for kw in imposter_kws):
        sigs["potential_imposter_syndrome"] = True
        sigs["framing_hint"]                = "Validate their worth explicitly before proceeding to matching"

    return sigs


def interpret_ownership_signals(text: str) -> dict[str, Any]:
    """Determine builder/owner vs executor/participant from how they describe their work."""
    lower = text.lower()
    sigs: dict[str, Any] = {}

    owner_kws = [
        "i decided", "i built", "my decision", "i proposed", "i pushed for",
        "i took ownership", "i owned", "without being asked", "on my own initiative",
        "proactively", "i noticed and fixed", "i redesigned", "i refactored without",
        "i architected",
    ]
    executor_kws = [
        "i was assigned", "i was asked to", "my manager told me",
        "the team decided", "we were told to", "the spec said",
        "following the design doc", "as per requirements", "handed to me",
    ]

    owner_count    = sum(1 for kw in owner_kws    if kw in lower)
    executor_count = sum(1 for kw in executor_kws if kw in lower)

    if owner_count >= 2 and owner_count > executor_count:
        sigs["ownership_mindset"] = "strong"
    elif executor_count >= 2 and executor_count > owner_count:
        sigs["ownership_mindset"] = "execution_focused"
        sigs["framing_hint"]      = "Probe ownership depth before flagging as high-ownership match"
    elif owner_count >= 1:
        sigs["ownership_mindset"] = "emerging"

    return sigs
