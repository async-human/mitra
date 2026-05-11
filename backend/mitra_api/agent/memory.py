"""
mitra_api/agent/memory.py

LLM-synthesized candidate and founder memory portraits.

Each portrait is a compact JSON object stored in the candidate_signals table
under the special key ``_memory``. It is injected into the system prompt at
the start of every agent turn so the agent has a rich, persistent picture of
who it is talking to without re-reading the full conversation history.

Public API
----------
build_candidate_memory(signals, intro_history, conversation_excerpt) -> str | None
build_founder_memory(signals, intro_history) -> str | None
inject_memory_into_context(system_prompt, memory, memory_type) -> str
"""

from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)

# Minimum useful signals before we bother building a portrait.
_MIN_SIGNALS = 5

_CANDIDATE_PORTRAIT_PROMPT = """\
You are building a compact memory portrait for a recruiting agent.

You will receive:
- SIGNALS: key/value facts gathered during intake
- INTRO_HISTORY: previous job introduction attempts and their outcomes
- CONVERSATION_EXCERPT: the most recent conversation turns

Synthesise a JSON object with these fields (omit fields you have no data for):
{
  "name": "Full Name",
  "current_role": "Job title @ Company",
  "years_exp": 5,
  "primary_stack": ["Python", "FastAPI"],
  "secondary_stack": ["React"],
  "industries": ["fintech", "B2B SaaS"],
  "strengths": ["backend systems", "API design"],
  "motivation": "one sentence — what drives them",
  "constraints": ["remote only", "no relocation"],
  "salary_expectation": "₹40–50 LPA",
  "open_to": ["Series A–C", "founding eng roles"],
  "not_interested_in": ["FAANG", "consulting"],
  "intro_outcomes": [{"company": "Acme", "role": "SWE", "status": "interview scheduled"}],
  "vibe": "one sentence describing communication style and personality"
}

Be concise. Use exact values from the signals; infer only when confident.
Reply with ONLY the JSON object — no markdown, no explanation."""

_FOUNDER_PORTRAIT_PROMPT = """\
You are building a compact memory portrait for a recruiting agent.

You will receive:
- SIGNALS: key/value facts about the founder / hiring manager
- INTRO_HISTORY: candidate introductions sent to this founder and their outcomes

Synthesise a JSON object with these fields (omit fields you have no data for):
{
  "name": "Full Name",
  "company": "Company name",
  "role": "Founder / VP Eng etc",
  "hiring_for": ["Backend Engineer", "Product Manager"],
  "stage": "Series A",
  "team_size": 12,
  "tech_stack": ["Go", "Postgres"],
  "must_haves": ["strong DSA", "startup experience"],
  "nice_to_haves": ["fintech background"],
  "deal_breakers": ["no remote"],
  "response_style": "one sentence — how they communicate (fast/slow, detailed/terse)",
  "intro_outcomes": [{"candidate": "Name", "role": "SWE", "status": "passed"}]
}

Be concise. Use exact values from the signals; infer only when confident.
Reply with ONLY the JSON object — no markdown, no explanation."""


async def build_candidate_memory(
    signals: dict[str, Any],
    intro_history: list[dict[str, Any]],
    conversation_excerpt: str = "",
) -> str | None:
    """
    Call the LLM to synthesise a candidate portrait from accumulated signals.
    Returns a JSON string (to be stored as-is in candidate_signals under '_memory'),
    or None if the call fails or signals are too sparse.
    """
    if len(signals) < _MIN_SIGNALS:
        return None

    try:
        from mitra_api.config import get_settings
        from mitra_api.llm.factory import get_llm_adapter
        from mitra_api.llm.types import ChatMessage

        s       = get_settings()
        adapter = get_llm_adapter(s)

        user_content = (
            f"SIGNALS:\n{json.dumps(signals, ensure_ascii=False, indent=2)}\n\n"
            f"INTRO_HISTORY:\n{json.dumps(intro_history, ensure_ascii=False, indent=2)}\n\n"
            f"CONVERSATION_EXCERPT:\n{conversation_excerpt[-2000:] if conversation_excerpt else '(none)'}"
        )

        result = await adapter.complete(
            model=s.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_CANDIDATE_PORTRAIT_PROMPT),
                ChatMessage(role="user",   content=user_content),
            ],
            tools=[],
            max_tokens=512,
            temperature=0.0,
        )

        raw = (result.content or "").strip()
        if not raw:
            return None

        # Validate it's parseable JSON before storing
        json.loads(raw)
        log.info("memory: built candidate portrait (%d chars)", len(raw))
        return raw

    except Exception:
        log.exception("memory: build_candidate_memory failed")
        return None


async def build_founder_memory(
    signals: dict[str, Any],
    intro_history: list[dict[str, Any]],
) -> str | None:
    """
    Call the LLM to synthesise a founder portrait from accumulated signals.
    Returns a JSON string or None on failure.
    """
    if not signals and not intro_history:
        return None

    try:
        from mitra_api.config import get_settings
        from mitra_api.llm.factory import get_llm_adapter
        from mitra_api.llm.types import ChatMessage

        s       = get_settings()
        adapter = get_llm_adapter(s)

        user_content = (
            f"SIGNALS:\n{json.dumps(signals, ensure_ascii=False, indent=2)}\n\n"
            f"INTRO_HISTORY:\n{json.dumps(intro_history, ensure_ascii=False, indent=2)}"
        )

        result = await adapter.complete(
            model=s.mitra_llm_model,
            messages=[
                ChatMessage(role="system", content=_FOUNDER_PORTRAIT_PROMPT),
                ChatMessage(role="user",   content=user_content),
            ],
            tools=[],
            max_tokens=512,
            temperature=0.0,
        )

        raw = (result.content or "").strip()
        if not raw:
            return None

        json.loads(raw)
        log.info("memory: built founder portrait (%d chars)", len(raw))
        return raw

    except Exception:
        log.exception("memory: build_founder_memory failed")
        return None


def inject_memory_into_context(
    system_prompt: str,
    memory: str | None,
    memory_type: str = "candidate",
) -> str:
    """
    Inject a memory portrait block into the system prompt.

    Inserts immediately after the first ``---`` separator line so it reads as
    authoritative context before any role-specific instructions. If no separator
    is found, appends to the end.

    Args:
        system_prompt: The original SYSTEM_PROMPT string.
        memory:        JSON string portrait (from candidate_signals['_memory']).
        memory_type:   "candidate" or "founder" — used in the injected header.

    Returns:
        Modified system prompt string.
    """
    if not memory:
        return system_prompt

    try:
        portrait = json.loads(memory)
    except Exception:
        log.warning("memory: could not parse memory JSON — skipping injection")
        return system_prompt

    lines_out: list[str] = []
    for field, label in (
        ("name",              "Name"),
        ("current_role",      "Current role"),
        ("years_exp",         "Experience"),
        ("primary_stack",     "Primary stack"),
        ("secondary_stack",   "Secondary stack"),
        ("industries",        "Industries"),
        ("strengths",         "Strengths"),
        ("motivation",        "Motivation"),
        ("constraints",       "Constraints"),
        ("salary_expectation","Salary expectation"),
        ("open_to",           "Open to"),
        ("not_interested_in", "Not interested in"),
        ("must_haves",        "Must-haves"),
        ("nice_to_haves",     "Nice-to-haves"),
        ("deal_breakers",     "Deal-breakers"),
        ("response_style",    "Response style"),
        ("vibe",              "Vibe"),
    ):
        val = portrait.get(field)
        if val is None:
            continue
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val) if val else None
        if val is not None:
            lines_out.append(f"  {label}: {val}")

    intro_outcomes = portrait.get("intro_outcomes")
    if intro_outcomes:
        lines_out.append("  Intro history:")
        for o in intro_outcomes:
            lines_out.append(
                f"    - {o.get('candidate') or o.get('company', '?')} "
                f"({o.get('role', '?')}): {o.get('status', '?')}"
            )

    if not lines_out:
        return system_prompt

    block = (
        f"\n[{memory_type.upper()} MEMORY — synthesised portrait]\n"
        + "\n".join(lines_out)
        + "\n[END MEMORY]\n"
    )

    # Insert after the first "---" separator
    sep = "\n---\n"
    idx = system_prompt.find(sep)
    if idx != -1:
        return system_prompt[: idx + len(sep)] + block + system_prompt[idx + len(sep):]

    return system_prompt + "\n" + block
