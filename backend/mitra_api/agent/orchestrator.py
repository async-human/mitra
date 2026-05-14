"""
mitra_api/agent/orchestrator.py  (production replacement)

Seven tools available to the agent
----------------------------------
1. search_jobs                 Vector search + LLM reranking against real Postgres jobs
2. remember_candidate_signals  Persist signals to Redis session + Postgres
3. get_salary_benchmark        India startup salary data by role/stage/seniority
4. web_market_research         Live web search (Tavily) for fresh third-party context
5. request_intro               Record intro + prepare founder message
6. check_intro_status         Look up status of a previously sent intro
7. parse_resume               Extract structured data from PDF sent on WhatsApp

Drop-in replacement for the existing orchestrator.py.
All other files (inbound.py, session_store.py, routes, etc.) stay unchanged.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

# phase: "start" | "end", name: tool function name from the catalog.
OnToolProgress = Callable[[str, str], Awaitable[None]]

from mitra_api.agent.memory import build_candidate_memory, inject_memory_into_context
from mitra_api.agent.prompts import OFFER_COACH_WEB_INTENT_OVERRIDE, SYSTEM_PROMPT
from mitra_api.agent.session_store import AgentSessionStore
from mitra_api.config import Settings, get_settings
from mitra_api.db.engine import get_session_factory
from mitra_api.llm.factory import get_llm_adapter
from mitra_api.llm.types import ChatMessage, ToolDefinition
from mitra_api.tools.candidates import get_signals as get_persisted_signals
from mitra_api.tools.candidates import persist_signals
from mitra_api.tools.intros import get_intro_status, request_intro
from mitra_api.tools.market_research import web_market_research
from mitra_api.tools.resume_parser import parse_resume_from_url, twilio_media_auth
from mitra_api.tools.salary_benchmark import get_salary_benchmark_async
from mitra_api.tools.search import search_jobs
from mitra_api.whatsapp.interactive_native import (
    InteractiveListRow,
    job_pick_rows_native_list,
    prelude_and_outro_for_native_list,
)
from mitra_api.whatsapp.job_cards import build_search_jobs_tool_payload, whatsapp_outbound_chain

log = logging.getLogger(__name__)

ToolRunner = Callable[[str, dict[str, Any]], Awaitable[str]]

# Keep aligned with mitra_api.tools.intros._SALARY_SIGNALS
_REQUEST_INTRO_SALARY_KEYS = (
    "salary_floor_lpa",
    "salary_target_lpa",
    "salary_min_lpa",
    "salary_max_lpa",
    "current_ctc_lpa",
)


def _build_request_intro_inline_patch(args: dict[str, Any]) -> dict[str, Any]:
    """Extract optional fields from request_intro tool args for gate + persistence."""
    inline: dict[str, Any] = {}
    if args.get("candidate_name"):
        inline["candidate_name"] = str(args["candidate_name"]).strip()
    ps = args.get("primary_stack")
    if ps:
        inline["primary_stack"] = ps
    if args.get("current_role"):
        inline["current_role"] = str(args["current_role"]).strip()
    cc = args.get("current_company")
    if cc is not None and str(cc).strip() != "":
        inline["current_company"] = str(cc).strip()
    for key in _REQUEST_INTRO_SALARY_KEYS:
        v = args.get(key)
        if v is None or v == "":
            continue
        try:
            inline[key] = int(round(float(v)))
        except (TypeError, ValueError):
            continue
    return inline


def _has_intro_salary_signal(signals: dict[str, Any]) -> bool:
    """True if at least one salary field satisfies the intro gate (see intros._SALARY_SIGNALS)."""
    return any(signals.get(k) for k in _REQUEST_INTRO_SALARY_KEYS)


@dataclass(frozen=True)
class AgentTurn:
    """Result of handling one inbound user message. Unchanged interface."""
    history_assistant_text: str
    native_list_rows: tuple[InteractiveListRow, ...]
    whatsapp_intro: str | None
    whatsapp_outro: tuple[str, ...]
    whatsapp_fallback_plain_parts: tuple[str, ...]
    job_whys: dict[str, str] = field(default_factory=dict)
    web_research_sources: tuple[dict[str, str], ...] = ()


# ── TOOL DEFINITIONS ─────────────────────────────────────────────────────────

def tool_catalog() -> list[ToolDefinition]:
    return [

        ToolDefinition(
            name="search_jobs",
            description=(
                "Search Mitra's job database using semantic vector search + AI reranking. "
                "Call when you have enough context: motivation + role type + at least one "
                "fit signal (stack, seniority, location, or sector). "
                "Returns formatted_cards to paste in your reply verbatim."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description of what the candidate wants.",
                    },
                    "location_hint": {
                        "type": "string",
                        "description": "City/country preference. e.g. 'Bengaluru', 'Remote India'.",
                    },
                    "seniority": {
                        "type": "string",
                        "enum": ["intern", "mid", "senior", "lead", "principal", "unknown"],
                    },
                    "employment_types": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["full_time", "contract", "unknown"]},
                    },
                    "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 8},
                },
                "required": ["query"],
            },
        ),

        ToolDefinition(
            name="remember_candidate_signals",
            description=(
                "Persist durable candidate facts to storage. "
                "Call whenever the candidate shares something worth keeping: "
                "stack, salary expectations, location, dealbreakers, motivation, "
                "notice period, stage preference. Do NOT call every turn — "
                "only when genuinely new information is shared."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "signals": {
                        "type": "object",
                        "description": (
                            "Key-value map of facts. Keys should be snake_case. "
                            "Examples: {\"primary_stack\": [\"Python\", \"FastAPI\"], "
                            "\"salary_target_lpa\": 45, "
                            "\"motivation\": \"wants to build 0→1 product\", "
                            "\"dealbreakers\": [\"crypto\", \"service companies\"]}"
                        ),
                    }
                },
                "required": ["signals"],
            },
        ),

        ToolDefinition(
            name="get_salary_benchmark",
            description=(
                "Return India startup salary benchmarks (P25/median/P75 in LPA) "
                "for a given role, startup stage, and seniority level. "
                "Use when a candidate asks about expected salary, whether an offer "
                "is fair, or how much they should ask for."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "description": "Role type. e.g. 'backend engineer', 'ML engineer', 'frontend'.",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Startup stage. e.g. 'Series A', 'seed', 'Series B'.",
                    },
                    "seniority": {
                        "type": "string",
                        "description": "Level. e.g. 'senior', 'lead', 'mid'.",
                    },
                },
                "required": ["role", "stage", "seniority"],
            },
        ),

        ToolDefinition(
            name="web_market_research",
            description=(
                "Search the public web for up-to-date market context (e.g. salary surveys, "
                "reports, hiring news, funding). Use when the candidate asks for *current* "
                "external data, broader market colour, or sources beyond Mitra's job database. "
                "Prefer get_salary_benchmark first for standard India startup CTC bands "
                "by role/stage/seniority — use this when they want live web sources, "
                "recent articles, or topics benchmarks do not cover. Results are snippets — "
                "tell them to verify key numbers on the linked pages."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Specific English search query. Include India, role, level, "
                            "and year when freshness matters. "
                            "Example: 'senior machine learning engineer salary India tech startup 2025 LPA report'"
                        ),
                    },
                },
                "required": ["query"],
            },
        ),

        ToolDefinition(
            name="request_intro",
            description=(
                "Send a warm introduction from the candidate to a specific founder. "
                "Call when the candidate explicitly asks to be introduced to a role. "
                "You MUST pass the candidate's name, stack, current role, and salary expectation "
                "(floor or target LPA) inline — they are required for the intro to send."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The job's external_id from search results. e.g. 'mtr-001'.",
                    },
                    "why_note": {
                        "type": "string",
                        "description": (
                            "1-2 sentences explaining why this candidate fits this specific role. "
                            "Reference their specific background and the role's requirements."
                        ),
                    },
                    "candidate_name": {
                        "type": "string",
                        "description": "Candidate's full name. e.g. 'Harshal Shinde'.",
                    },
                    "primary_stack": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Main technologies. e.g. ['Python', 'FastAPI', 'LLMs'].",
                    },
                    "current_role": {
                        "type": "string",
                        "description": "Current job title. e.g. 'Senior AI Engineer'.",
                    },
                    "current_company": {
                        "type": "string",
                        "description": "Current employer. e.g. 'Infinite Possibilities'.",
                    },
                    "salary_target_lpa": {
                        "type": "number",
                        "description": (
                            "Expected compensation in LPA (annual). Use the candidate's confirmed "
                            "target or the high end of their stated range. Required for the intro "
                            "unless already saved via remember_candidate_signals."
                        ),
                    },
                    "salary_floor_lpa": {
                        "type": "number",
                        "description": "Minimum acceptable LPA if they gave a floor instead of a single target.",
                    },
                },
                "required": ["job_id", "why_note", "candidate_name", "primary_stack", "current_role"],
            },
        ),

        ToolDefinition(
            name="check_intro_status",
            description=(
                "Check the current status of a previously sent introduction. "
                "Use when a candidate asks 'any update?', 'did they reply?', "
                "'what happened with that intro?'"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The job's external_id. e.g. 'mtr-001'.",
                    },
                },
                "required": ["job_id"],
            },
        ),

        ToolDefinition(
            name="parse_resume",
            description=(
                "Extract structured information from a resume PDF the candidate sent. "
                "Call when the candidate shares a PDF media message or says they're "
                "sharing their CV. The extracted signals are automatically saved."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "media_url": {
                        "type": "string",
                        "description": "URL of the PDF media attachment from WhatsApp/Twilio.",
                    },
                },
                "required": ["media_url"],
            },
        ),

    ]


# ── TOOL RUNNERS ─────────────────────────────────────────────────────────────

def build_tool_runner(
    session_id: str,
    sessions: AgentSessionStore,
    settings: Settings,
) -> ToolRunner:
    """Build the async tool dispatcher for one agent turn."""

    db_factory = get_session_factory()

    async def _run(name: str, args: dict[str, Any]) -> str:

        # ── 1. search_jobs ────────────────────────────────────────────────────
        if name == "search_jobs":
            # Get current signals for query enrichment
            candidate_signals = await sessions.get_signals(session_id)

            async with db_factory() as db:
                jobs = await search_jobs(
                    query=str(args.get("query", "")),
                    candidate_signals=candidate_signals,
                    session=db,
                    seniority=str(args.get("seniority", "unknown")),
                    location_hint=str(args.get("location_hint", "")),
                    employment_types=args.get("employment_types") or [],
                    limit=int(args.get("limit") or 5),
                )

            # Build WhatsApp card payload — same format as before
            picks = [
                {
                    "id":        str(j.get("external_id") or j.get("id", "")),
                    "title":     j.get("title", "Role"),
                    "company":   j.get("company", ""),
                    "location":  j.get("location", ""),
                    "why":       j.get("why") or j.get("summary", ""),
                    "tags":      _build_tags(j),
                    "fit_label": j.get("fit_label", "88% fit"),
                }
                for j in jobs
            ] or [{"note": "no strong matches", "suggestion": "try widening your role or location"}]

            payload = build_search_jobs_tool_payload(picks, query_echo=args.get("query"))
            return json.dumps(payload, ensure_ascii=False)

        # ── 2. remember_candidate_signals ─────────────────────────────────────
        if name == "remember_candidate_signals":
            sig = args.get("signals")
            if not isinstance(sig, dict):
                sig = {}
            cleaned = {str(k): v for k, v in sig.items()}

            # Write to session store (fast path — in Redis or memory)
            await sessions.merge_signals(session_id, cleaned)

            # Write to Postgres (durable path — survives restarts)
            try:
                async with db_factory() as db:
                    await persist_signals(session_id, cleaned, session=db)
            except Exception:
                log.exception("Postgres signal persist failed for %s (session store updated OK)", session_id)

            # Fire memory build in background once enough signals have accumulated
            try:
                all_signals = await sessions.get_signals(session_id)
                non_meta = {k: v for k, v in all_signals.items() if not k.startswith("_")}
                if len(non_meta) >= 5:
                    asyncio.create_task(
                        _build_and_persist_memory(session_id, non_meta, db_factory),
                        name=f"memory-build-{session_id}",
                    )
            except Exception:
                log.debug("memory build scheduling failed (non-critical)")

            return json.dumps({"ok": True, "stored_keys": list(cleaned.keys())}, ensure_ascii=False)

        # ── 3. get_salary_benchmark ───────────────────────────────────────────
        if name == "get_salary_benchmark":
            result = await get_salary_benchmark_async(
                role=str(args.get("role", "backend engineer")),
                stage=str(args.get("stage", "Series A")),
                seniority=str(args.get("seniority", "senior")),
            )
            return json.dumps(result, ensure_ascii=False)

        # ── 4. web_market_research ─────────────────────────────────────────────
        if name == "web_market_research":
            result = await web_market_research(
                query=str(args.get("query", "")),
                settings=settings,
            )
            return json.dumps(result, ensure_ascii=False)

        # ── 5. request_intro ──────────────────────────────────────────────────
        if name == "request_intro":
            inline = _build_request_intro_inline_patch(args)
            async with db_factory() as db:
                if inline:
                    await sessions.merge_signals(session_id, inline)
                    try:
                        await persist_signals(session_id, inline, session=db)
                    except Exception:
                        log.exception("pre-intro inline signal persist failed for %s", session_id)

                result = await request_intro(
                    candidate_phone=session_id,
                    job_external_id=str(args.get("job_id", "")),
                    why_note=str(args.get("why_note", "")),
                    session=db,
                    inline_signal_patch=inline or None,
                )
            return json.dumps(result, ensure_ascii=False)

        # ── 6. check_intro_status ─────────────────────────────────────────────
        if name == "check_intro_status":
            async with db_factory() as db:
                result = await get_intro_status(
                    candidate_phone=session_id,
                    job_external_id=str(args.get("job_id", "")),
                    session=db,
                )
            return json.dumps(result, ensure_ascii=False)

        # ── 7. parse_resume ───────────────────────────────────────────────────
        if name == "parse_resume":
            media_url = str(args.get("media_url", ""))
            if not media_url:
                return json.dumps({"ok": False, "error": "no media_url provided"})

            auth = twilio_media_auth(settings)
            extracted = await parse_resume_from_url(media_url, auth_headers=auth)

            if extracted:
                # Persist extracted signals immediately
                await sessions.merge_signals(session_id, extracted)
                try:
                    async with db_factory() as db:
                        await persist_signals(session_id, extracted, session=db)
                except Exception:
                    log.exception("Postgres persist failed after resume parse")

                return json.dumps({
                    "ok": True,
                    "extracted_keys": list(extracted.keys()),
                    "summary": f"Got it — I've read your CV and noted your background as a "
                               f"{extracted.get('current_role', 'engineer')} with "
                               f"{extracted.get('years_experience', 'several')} years of experience.",
                }, ensure_ascii=False)

            return json.dumps({"ok": False, "error": "could not extract text from PDF"})

        return json.dumps({"error": f"unknown tool: {name}"})

    return _run


_THIN_MARKERS = ("not specified", "several years", "their current company", "+91")


async def _load_weak_intros_note(candidate_phone: str, db_factory) -> str | None:
    """
    Return a system-level nudge when the candidate has thin pending intros.

    If signals are already in DB → tell agent to call request_intro NOW with the inline values.
    If signals missing → tell agent to extract them from the conversation and call request_intro.
    Never tells the agent to ask for re-confirmation of info already given.
    """
    try:
        from mitra_api.db.models import Candidate, CandidateSignal, Intro, IntroStatus, Job
        from sqlalchemy import select as sa_select

        async with db_factory() as db:
            candidate = (await db.execute(
                sa_select(Candidate).where(Candidate.phone == candidate_phone)
            )).scalar_one_or_none()
            if not candidate:
                return None

            signal_rows = (await db.execute(
                sa_select(CandidateSignal).where(CandidateSignal.candidate_id == candidate.id)
            )).scalars().all()
            signals: dict[str, Any] = {row.key: row.value for row in signal_rows}
            if candidate.name:
                signals.setdefault("candidate_name", candidate.name)
            if candidate.current_role:
                signals.setdefault("current_role", candidate.current_role)

            rows = (await db.execute(
                sa_select(Intro, Job)
                .join(Job, Intro.job_id == Job.id)
                .where(
                    Intro.candidate_id == candidate.id,
                    Intro.status.in_([IntroStatus.sent, IntroStatus.acknowledged]),
                )
            )).all()

            if not rows:
                return None

            weak = [
                {"job_id": job.external_id or str(job.id), "role": job.title, "company": job.company}
                for intro, job in rows
                if any(m in (intro.intro_note or "") for m in _THIN_MARKERS)
            ]
            if not weak:
                return None

            items = "; ".join(
                f"{w['role']} at {w['company']} (job_id: {w['job_id']})" for w in weak
            )
            name    = signals.get("candidate_name", "")
            stack   = signals.get("primary_stack", [])
            role    = signals.get("current_role", "")
            company = signals.get("current_company", "")

            if name and stack and role and _has_intro_salary_signal(signals):
                return (
                    f"CONTEXT: Thin intro(s) exist for {items}. "
                    f"Profile confirmed — name='{name}', stack={stack}, role='{role}', "
                    f"company='{company}'. "
                    f"If the candidate asks about these intros or wants to strengthen them, "
                    f"call request_intro with these inline fields plus salary_target_lpa or "
                    f"salary_floor_lpa if not already stored. "
                    f"Wait for explicit intent — do NOT auto-fire intros if the candidate is "
                    f"asking a new question or starting a fresh search."
                )
            else:
                missing = [k for k in ("candidate_name", "primary_stack", "current_role")
                           if not signals.get(k)]
                if not _has_intro_salary_signal(signals):
                    missing.append("salary_expectation_lpa")
                return (
                    f"CONTEXT: Thin intro(s) for {items} were sent with incomplete profile info. "
                    f"Missing signals: {', '.join(missing)}. "
                    f"If the candidate's message today is about strengthening these intros or following up, "
                    f"collect the missing info and call request_intro. "
                    f"Do NOT interrupt a new job search or fresh conversation to chase these — "
                    f"only act if the candidate brings up these intros explicitly."
                )

    except Exception:
        log.exception("_load_weak_intros_note failed for %s", candidate_phone)
        return None


async def _build_and_persist_memory(
    session_id: str,
    signals: dict[str, Any],
    db_factory: Any,
) -> None:
    """Background task: build a candidate memory portrait and infer trajectory, then persist both."""
    try:
        to_persist: dict[str, Any] = {}

        portrait_json = await build_candidate_memory(
            signals=signals,
            intro_history=[],
        )
        if portrait_json:
            to_persist["_memory"] = portrait_json

        # Co-fire trajectory inference — no extra LLM round trip since it runs concurrently
        try:
            from mitra_api.tools.intelligence import infer_candidate_trajectory
            trajectory = await infer_candidate_trajectory(signals)
            if trajectory:
                to_persist["_trajectory"] = trajectory
        except Exception:
            log.debug("trajectory inference skipped (non-critical)")

        if to_persist:
            async with db_factory() as db:
                await persist_signals(session_id, to_persist, session=db)
            log.info(
                "memory: persisted %s for %s",
                " + ".join(to_persist.keys()), session_id,
            )
    except Exception:
        log.exception("_build_and_persist_memory failed for %s", session_id)


async def _load_candidate_signals(
    *,
    session_id: str,
    sessions: AgentSessionStore,
) -> dict[str, Any]:
    """
    Resolve candidate signals with DB fallback.

    Session store is fast-path (Redis/in-memory). If it's empty (common after
    backend restart in dev), hydrate it from Postgres so the agent still
    remembers durable profile facts.
    """
    try:
        cached = await sessions.get_signals(session_id)
    except Exception:
        log.warning("Redis get_signals failed for %s — falling back to DB", session_id)
        cached = {}

    if cached:
        return cached

    db_factory = get_session_factory()
    try:
        async with db_factory() as db:
            persisted = await get_persisted_signals(session_id, session=db)
    except Exception:
        log.exception("failed to load persisted signals for %s", session_id)
        return {}

    if persisted:
        try:
            await sessions.merge_signals(session_id, persisted)
        except Exception:
            log.warning("Redis merge_signals failed for %s — DB signals still loaded", session_id)
    return persisted


# ── AGENT TURN ────────────────────────────────────────────────────────────────

async def run_agent_turn(
    *,
    whatsapp_sender_id: str,
    user_text: str,
    sessions: AgentSessionStore,
    settings: Settings | None = None,
    media_url: str | None = None,     # set if WhatsApp message has a PDF attachment
    media_type: str | None = None,    # "application/pdf" etc
    fresh_start: bool = False,        # True when user explicitly asked to start over
    web_intent: str | None = None,    # e.g. "offer_coach" from Mitra web app
    on_tool_progress: OnToolProgress | None = None,
) -> AgentTurn:
    """
    Process one inbound WhatsApp message and return the agent's response.
    Interface is backwards-compatible with the previous orchestrator.
    """
    s = settings or get_settings()
    adapter    = get_llm_adapter(s)
    tools      = tool_catalog()
    db_factory = get_session_factory()
    run_tool   = build_tool_runner(whatsapp_sender_id, sessions, s)
    known_signals = await _load_candidate_signals(
        session_id=whatsapp_sender_id,
        sessions=sessions,
    )

    if fresh_start:
        await sessions.merge_signals(whatsapp_sender_id, {"_offer_coach_thread": False})
        offer_coach_thread = False
    else:
        offer_coach_thread = bool(known_signals.get("_offer_coach_thread"))

    # Separate internal meta-keys — never exposed in the raw signals dump
    candidate_memory     = known_signals.pop("_memory", None)
    last_interpretation  = known_signals.pop("_last_interpretation", None)
    trajectory_data      = known_signals.pop("_trajectory", None)
    last_reflection      = known_signals.pop("_reflection", None)
    implicit_contradictions = known_signals.pop("_implicit_contradictions", None) or []
    probed_dimensions       = known_signals.pop("_probed_dimensions", None) or []
    asked_log_raw           = known_signals.pop("_asked_log", None) or []
    # Remove all _implicit_* and other _-prefixed keys from the raw dump;
    # they are surfaced via the [CONVERSATION STATE] block instead.
    implicit_signals = {k: v for k, v in list(known_signals.items()) if k.startswith("_")}
    for k in implicit_signals:
        known_signals.pop(k, None)

    # ── Rule-based signal extraction (fast, free, synchronous) ───────────────
    from mitra_api.tools.signal_interpreter import (
        interpret_hesitation_signals,
        interpret_ownership_signals,
        interpret_salary_mention,
        interpret_timing_signals,
    )

    rule_signals: dict[str, Any] = {}
    rule_signals.update(interpret_salary_mention(user_text, known_signals))
    rule_signals.update(interpret_timing_signals(user_text))
    rule_signals.update(interpret_hesitation_signals(user_text))
    rule_signals.update(interpret_ownership_signals(user_text))

    if rule_signals:
        await sessions.merge_signals(whatsapp_sender_id, rule_signals)
        known_signals.update(rule_signals)
        log.debug("rule-based signals: %s", list(rule_signals.keys()))

    # ── Contradiction detection (rule-based, synchronous, free) ──────────────
    # Detects stated-vs-revealed inconsistencies on 6 dimensions. Surfaced to
    # the agent via [CANDIDATE INTERNAL TENSION] block, never to founders
    # until human-reviewed.
    try:
        from mitra_api.tools.contradictions import (
            detect_contradictions,
            merge_contradictions,
        )
        fresh_contradictions = detect_contradictions(known_signals)
        if fresh_contradictions:
            implicit_contradictions = merge_contradictions(
                implicit_contradictions, fresh_contradictions
            )
            await sessions.merge_signals(
                whatsapp_sender_id,
                {"_implicit_contradictions": implicit_contradictions},
            )
            log.info(
                "[agent:%s] contradictions detected: %s",
                whatsapp_sender_id,
                [c["dimension"] for c in fresh_contradictions],
            )
    except Exception:
        log.debug("contradiction detection failed (non-critical)", exc_info=True)

    # Pull framing_hint out before the signals dump — it's an agent instruction,
    # not a profile fact, and it gets its own formatted [FRAMING: ...] block later.
    framing_hint = known_signals.pop("framing_hint", None)

    # ── Build message list with cache-optimised ordering ──────────────────────
    #
    # Cache breakpoints (cache_control=ephemeral) must appear on content that is
    # stable across turns so the prefix before each breakpoint is byte-identical.
    # Ordering from most-stable to least-stable maximises hit rate:
    #
    #   1. SYSTEM_PROMPT      — static, never changes             → ephemeral cache
    #   2. Memory portrait    — rebuilt rarely (hours/days)       → ephemeral cache
    #   3. Known signals      — changes when new signals saved    → no cache
    #   4. Transcript prefix  — all but last 2 turns are stable   → ephemeral cache on boundary
    #   5. Last 2 turns       — always fresh                      → no cache
    #   6. Per-turn ephemeral context (fresh_start / returning / weak_intros / resume)
    #   7. Current user message
    #
    msgs: list[ChatMessage] = [
        ChatMessage(
            role="system",
            content=SYSTEM_PROMPT,
            cache_control={"type": "ephemeral"},
        )
    ]

    # Memory portrait — separate message so SYSTEM_PROMPT stays byte-identical
    if candidate_memory:
        memory_text = inject_memory_into_context("", candidate_memory, "candidate").strip()
        if memory_text:
            msgs.append(
                ChatMessage(
                    role="system",
                    content=memory_text,
                    cache_control={"type": "ephemeral"},
                )
            )

    # Trajectory intelligence — inferred async, rare updates → cache-friendly
    if trajectory_data and isinstance(trajectory_data, dict):
        traj_parts: list[str] = []
        if trajectory_data.get("trajectory_label"):
            traj_parts.append(f"Trajectory: {trajectory_data['trajectory_label']}")
        if trajectory_data.get("real_stage_fit"):
            traj_parts.append(f"Real stage fit: {trajectory_data['real_stage_fit']}")
        if trajectory_data.get("engineer_type"):
            traj_parts.append(f"Engineer type: {trajectory_data['engineer_type']}")
        if trajectory_data.get("hidden_constraint"):
            traj_parts.append(f"Hidden constraint: {trajectory_data['hidden_constraint']}")
        if traj_parts:
            msgs.append(ChatMessage(
                role="system",
                content="[CANDIDATE INTELLIGENCE: " + " · ".join(traj_parts) + "]",
                cache_control={"type": "ephemeral"},
            ))

    transcript: list[ChatMessage] = []

    if fresh_start:
        # User explicitly asked to start over — drop history so the agent starts cleanly.
        # Profile signals are kept (we remember who they are, don't re-ask basics).
        log.info("[agent:%s] fresh_start=True — skipping old transcript", whatsapp_sender_id)
    else:
        try:
            transcript = await sessions.get_transcript(whatsapp_sender_id)
            # Put a cache breakpoint on the last stable user message in the transcript
            # (everything before the final two turns is stable and can be cached).
            if len(transcript) > 4:
                stable_boundary = len(transcript) - 4
                # Find the last user message at or before the stable boundary
                for i in range(stable_boundary, -1, -1):
                    if transcript[i].role == "user" and not transcript[i].cache_control:
                        transcript[i] = transcript[i].model_copy(
                            update={"cache_control": {"type": "ephemeral"}}
                        )
                        break
            msgs.extend(transcript)
        except Exception:
            log.warning("Redis get_transcript failed for %s — starting with empty history", whatsapp_sender_id)

    # Detect a returning candidate re-opening the web chat.
    # The web app fires callApi("") on mount; this flag suppresses intake/signal
    # injections that would override the welcome-back instruction below.
    is_new_web_session = (
        not fresh_start
        and not user_text.strip()
        and bool(transcript)
        and bool(known_signals)
    )

    if known_signals:
        msgs.append(
            ChatMessage(
                role="system",
                content=(
                    "Known candidate profile signals (use as prior context unless user corrects them): "
                    + json.dumps(known_signals, ensure_ascii=False)
                ),
            )
        )

    # NOTE: [INTAKE READINESS], [SIGNAL INTELLIGENCE], [BEHAVIORAL STATE], and
    # [CANDIDATE INTERNAL TENSION] are no longer injected individually.
    # They are integrated into the single [CONVERSATION STATE] block below,
    # produced by conversation_state.compute_state(). See the integration block
    # further down (after the fresh_start / returning / new_session branches).

    if fresh_start and known_signals:
        name = known_signals.get("candidate_name", "")
        greeting = f", {name.split()[0]}" if name else ""
        msgs.append(ChatMessage(
            role="system",
            content=(
                f"FRESH START — the candidate asked to start over{greeting}. "
                f"Their profile is already known (signals above) — do NOT re-ask for name, stack, or history. "
                f"Treat this as a new job search session. Ask ONE open question about what they're looking "
                f"for this time, acknowledging you remember their background. "
                f"Do NOT send or mention any previous intros unless the candidate brings them up."
            ),
        ))
    elif known_signals and not transcript:
        # Returning candidate with no transcript — signals survived Redis expiry (loaded from Postgres).
        name = known_signals.get("candidate_name", "")
        greeting = f" ({name})" if name else ""
        msgs.append(ChatMessage(
            role="system",
            content=(
                f"RETURNING CANDIDATE{greeting} — their profile was loaded from durable storage "
                f"but the conversation history has expired. "
                f"Do NOT restart the intake or re-ask for information already in their profile. "
                f"Greet them warmly as someone you already know, briefly acknowledge what you remember "
                f"(role, stack, motivation), and ask what they'd like to do: "
                f"see fresh recommendations, check on a previous intro, or update their preferences. "
                f"One question only."
            ),
        ))
        log.info("[agent:%s] returning candidate — signals present, transcript expired", whatsapp_sender_id)

    elif not user_text.strip() and transcript and known_signals:
        # New web chat session — returning candidate who has an active conversation history.
        # The web app fires callApi("") on mount; we detect this and generate a proper
        # welcome-back summary instead of continuing mid-conversation.
        name = known_signals.get("candidate_name", "")
        first = name.split()[0] if name else ""

        # Pull the most concrete signal available for the recap line (values may be str or list)
        def _recap_line(v: Any) -> str:
            if v is None or v == "":
                return ""
            if isinstance(v, list):
                return ", ".join(str(x) for x in v if x is not None and str(x).strip() != "")
            return str(v).strip()

        role_hint   = _recap_line(known_signals.get("current_role") or known_signals.get("what_they_want"))
        stack_hint  = _recap_line(known_signals.get("primary_stack"))
        motivation  = _recap_line(known_signals.get("motivation"))
        recap_parts = [p for p in [role_hint, stack_hint, motivation] if p]
        recap_hint  = f"Known context to reference: {'; '.join(recap_parts[:2])}. " if recap_parts else ""

        msgs.append(ChatMessage(
            role="system",
            content=(
                "◆ NEW SESSION — THIS OVERRIDES ALL OTHER INSTRUCTIONS FOR THIS TURN ◆\n\n"
                "The candidate has re-opened the web chat after a previous session. "
                "Generate the OPENING message of this new session — not a continuation.\n\n"
                "EXACT STRUCTURE (3 sentences max):\n"
                f"1. Greet them warmly{' by name (' + first + ')' if first else ''}.\n"
                "2. In ONE sentence, recap the most specific thing from the last session — "
                "their target role, stack, what they're looking for, or a concern they raised. "
                f"{recap_hint}"
                "Do NOT say 'last time we discussed' — just reference the fact naturally.\n"
                "3. Ask ONE question: would they like to see fresh job matches, "
                "continue from where they left off, or update their preferences?\n\n"
                "HARD RULES FOR THIS TURN:\n"
                "- Do NOT continue mid-conversation or respond to the last message in the transcript.\n"
                "- Do NOT ask any intake questions (motivation, challenges, stack, salary).\n"
                "- Ignore any [CONVERSATION STATE] block — it is not injected on a new session, but if seen, defer to these instructions.\n"
                "- One question only, about how they'd like to proceed."
            ),
        ))
        log.info("[agent:%s] new web session — returning candidate, transcript present", whatsapp_sender_id)

    # ── [CONVERSATION STATE] — single integration block ─────────────────────
    # Replaces the previous [SIGNAL INTELLIGENCE], [INTAKE READINESS],
    # [BEHAVIORAL STATE], and [CANDIDATE INTERNAL TENSION] blocks. The
    # ConversationState view is computed once and rendered into one prompt
    # block telling the agent exactly what to do this turn.
    #
    # Suppressed on new web sessions / fresh_start so the override branches
    # above remain authoritative.
    if not is_new_web_session and not fresh_start:
        try:
            from mitra_api.agent.conversation_state import (
                compute_state,
                load_asked_log,
            )
            from mitra_api.tools.intelligence import score_conversation_quality

            asked_log = load_asked_log(asked_log_raw)
            quality   = score_conversation_quality(known_signals)
            state = compute_state(
                turn_idx=len(transcript) // 2 + 1,
                known_signals=known_signals,
                transcript_len=len(transcript),
                last_reflection=last_reflection,
                last_interpretation=last_interpretation,
                contradictions=implicit_contradictions,
                probed_dimensions=probed_dimensions,
                asked_log=asked_log,
                readiness_pct=int(quality.get("score", 0)),
                framing_hint=framing_hint,
            )
            msgs.append(ChatMessage(role="system", content=state.to_prompt_block()))

            # If next_action is probe_tension, mark dimension as probed so the
            # same tension isn't raised again next turn.
            if state.next_action.kind == "probe_tension" and state.next_action.tension:
                new_probed = list(probed_dimensions) + [state.next_action.tension]
                await sessions.merge_signals(
                    whatsapp_sender_id,
                    {"_probed_dimensions": new_probed},
                )

            log.info(
                "[agent:%s] state — stage=%s readiness=%d%% action=%s",
                whatsapp_sender_id, state.stage, state.readiness_pct,
                state.next_action.to_block_line(),
            )
        except Exception:
            log.debug("conversation state computation failed (non-critical)", exc_info=True)

    # Inject weak-intro nudge — drives proactive strengthening without candidate having to ask.
    # Suppressed on fresh_start so the agent doesn't immediately re-fire old intros.
    if not fresh_start:
        weak_note = await _load_weak_intros_note(whatsapp_sender_id, db_factory)
        if weak_note:
            msgs.append(ChatMessage(role="system", content=weak_note))

    if web_intent == "offer_coach":
        await sessions.merge_signals(whatsapp_sender_id, {"_offer_coach_thread": True})
        offer_coach_thread = True

    if whatsapp_sender_id.startswith("web:") and offer_coach_thread:
        try:
            from mitra_api.tools.candidate_offer_context import build_offer_coaching_context_block

            offer_block = await build_offer_coaching_context_block(whatsapp_sender_id, db_factory)
            if offer_block:
                msgs.append(ChatMessage(role="system", content=offer_block))
            elif web_intent == "offer_coach":
                msgs.append(
                    ChatMessage(
                        role="system",
                        content=(
                            "[CANDIDATE PIPELINE — FACTS ON FILE (Mitra DB)]\n"
                            "No candidate record was found or the database could not be read. "
                            "Ask what offer details they have; they can also check Mitra → Introductions."
                        ),
                    )
                )
        except Exception:
            log.exception("[agent:%s] offer coaching context load failed", whatsapp_sender_id)

    if web_intent == "offer_coach":
        msgs.append(ChatMessage(role="system", content=OFFER_COACH_WEB_INTENT_OVERRIDE))
        log.info("[agent:%s] web_intent=offer_coach — injected offer coaching override", whatsapp_sender_id)

    # Auto-parse PDF resume before the LLM turn so the agent gets structured data,
    # not a raw URL it has to figure out what to do with.
    # Use a sentinel for the session-open ping so the LLM doesn't receive empty content.
    user_content = user_text.strip() or "[session opened]"
    if media_url and media_type and "pdf" in media_type.lower():
        try:
            from mitra_api.tools.resume_parser import (
                missing_follow_up_questions,
                parse_resume_from_url,
                twilio_media_auth,
            )
            auth = twilio_media_auth(s)
            parsed = await parse_resume_from_url(media_url, auth_headers=auth)

            if parsed:
                await sessions.merge_signals(whatsapp_sender_id, parsed)
                try:
                    async with db_factory() as db:
                        await persist_signals(whatsapp_sender_id, parsed, session=db)
                except Exception:
                    log.exception("Failed to persist resume signals for %s", whatsapp_sender_id)

                next_questions = missing_follow_up_questions(parsed, known_signals)
                next_q = next_questions[0] if next_questions else None

                resume_note = (
                    f"RESUME PARSED SUCCESSFULLY — do NOT call parse_resume tool again. "
                    f"The candidate sent their CV. "
                    f"Extracted signals (already saved to DB): {json.dumps(parsed, ensure_ascii=False)}. "
                    f"React warmly and specifically — mention their actual name, role, stack, "
                    f"and something specific that stood out. "
                    f"Then ask exactly ONE follow-up question about: {next_q}. "
                    f"Do NOT ask for information already extracted from the CV."
                )
                if not next_q:
                    resume_note = (
                        f"RESUME PARSED SUCCESSFULLY — do NOT call parse_resume tool again. "
                        f"Extracted signals: {json.dumps(parsed, ensure_ascii=False)}. "
                        f"You have a complete picture. React warmly to what you found, "
                        f"then offer to search for matching roles immediately."
                    )
                msgs.append(ChatMessage(role="system", content=resume_note))
                log.info("Auto-parsed resume for %s: %d signals", whatsapp_sender_id, len(parsed))
            else:
                msgs.append(ChatMessage(
                    role="system",
                    content=(
                        "The candidate sent a PDF but text could not be extracted "
                        "(possibly an image-based or scanned PDF). "
                        "Tell them warmly that you couldn't read it, and ask them to "
                        "share their name, current role, and tech stack directly in chat."
                    ),
                ))
        except Exception:
            log.exception("Auto-parse resume failed for %s", whatsapp_sender_id)

    msgs.append(ChatMessage(role="user", content=user_content))
    persist_from = len(msgs) - 1

    # ── Background deep interpretation (Haiku, async) ─────────────────────────
    # Snapshot the conversation *now* so the background coroutine gets a stable
    # copy — not a live reference to msgs which continues to grow during the loop.
    _history_snapshot = [
        {"role": m.role, "content": m.content or ""}
        for m in msgs
        if m.role in ("user", "assistant") and m.content
    ][-8:]
    _signals_snapshot = {k: v for k, v in known_signals.items() if not k.startswith("_")}
    _session_id_snap  = whatsapp_sender_id

    async def _run_interpretation() -> None:
        try:
            from mitra_api.tools.signal_interpreter import (
                extract_implicit_signals,
                interpret_candidate_message,
            )
            interp = await interpret_candidate_message(
                user_text, _history_snapshot, _signals_snapshot
            )
            if not interp:
                return
            implicit = extract_implicit_signals(interp)
            implicit["_last_interpretation"] = interp
            await sessions.merge_signals(_session_id_snap, implicit)
            try:
                async with db_factory() as db:
                    await persist_signals(_session_id_snap, implicit, session=db)
            except Exception:
                log.debug("implicit signal persist failed (non-critical)")
        except Exception:
            log.debug("background interpretation failed (non-critical)", exc_info=True)

    # Skip interpretation for the session-open ping — there's no real user message
    # to interpret and we don't want to overwrite _last_interpretation with noise.
    if not is_new_web_session:
        asyncio.create_task(_run_interpretation(), name=f"interp-{whatsapp_sender_id}")

    # Reflection runs after the turn completes (final_text not yet known here).
    # We schedule it below once we have the assistant response.
    _reflection_args = {
        "session_id":  whatsapp_sender_id,
        "user_text":   user_content,
        "signals":     _signals_snapshot,
        "db_factory":  db_factory,
        "sessions":    sessions,
    }

    last_search_jobs_payload: dict[str, Any] | None = None
    web_research_accum: list[dict[str, str]] = []
    web_research_seen_urls: set[str] = set()
    final_text: str | None = None
    rounds = 0

    log.info(
        "[agent:%s] turn start — model=%s signals=%s msg=%.80r",
        whatsapp_sender_id, s.mitra_llm_model,
        list(known_signals.keys()) if known_signals else [],
        user_content,
    )

    while rounds < s.mitra_agent_max_tool_rounds:
        rounds += 1
        log.info("[agent:%s] llm round %d", whatsapp_sender_id, rounds)

        result = await adapter.complete(
            model=s.mitra_llm_model,
            messages=msgs,
            tools=tools,
            max_tokens=s.mitra_llm_max_tokens,
            temperature=s.mitra_llm_temperature,
        )
        assistant_tool_calls = list(result.tool_calls or [])

        log.info(
            "[agent:%s] llm round %d — finish_reason=%s tool_calls=%s",
            whatsapp_sender_id, rounds,
            result.finish_reason,
            [tc.name for tc in assistant_tool_calls] or "none",
        )

        if assistant_tool_calls:
            msgs.append(ChatMessage(
                role="assistant",
                content=result.content,
                tool_calls=assistant_tool_calls,
            ))
            for tc in assistant_tool_calls:
                try:
                    parsed = json.loads(tc.arguments) if tc.arguments else {}
                    if not isinstance(parsed, dict):
                        parsed = {"_invalid": parsed}
                except json.JSONDecodeError:
                    parsed = {"_invalid_json": tc.arguments}

                log.info(
                    "[agent:%s] tool call — %s args=%s",
                    whatsapp_sender_id, tc.name,
                    {k: v for k, v in parsed.items() if k != "query"} if tc.name != "search_jobs"
                    else {"query": str(parsed.get("query", ""))[:120]},
                )

                if on_tool_progress:
                    try:
                        await on_tool_progress("start", tc.name)
                    except Exception:
                        log.debug("on_tool_progress(start) failed", exc_info=True)
                try:
                    out = await run_tool(tc.name, parsed)
                    if tc.name == "search_jobs":
                        try:
                            payload = json.loads(out)
                            last_search_jobs_payload = payload
                            jobs = payload.get("jobs") or []
                            no_match = len(jobs) == 1 and jobs[0].get("note")
                            log.info(
                                "[agent:%s] search_jobs returned %d job(s)%s: %s",
                                whatsapp_sender_id, 0 if no_match else len(jobs),
                                " (no match)" if no_match else "",
                                [(j.get("title"), j.get("company")) for j in jobs[:5]] if not no_match else jobs[0],
                            )
                        except json.JSONDecodeError:
                            log.warning("[agent:%s] search_jobs result was not valid JSON", whatsapp_sender_id)
                    elif tc.name == "web_market_research":
                        try:
                            payload = json.loads(out)
                            if payload.get("ok") and isinstance(payload.get("results"), list):
                                for r in payload["results"]:
                                    if not isinstance(r, dict):
                                        continue
                                    url = str(r.get("url") or "").strip()
                                    if not url or url in web_research_seen_urls:
                                        continue
                                    web_research_seen_urls.add(url)
                                    title = str(r.get("title") or "").strip() or url
                                    web_research_accum.append(
                                        {"title": title[:400], "url": url[:800]}
                                    )
                        except json.JSONDecodeError:
                            log.debug(
                                "[agent:%s] web_market_research result not JSON",
                                whatsapp_sender_id,
                            )
                        log.info("[agent:%s] tool web_market_research completed OK", whatsapp_sender_id)
                    else:
                        log.info("[agent:%s] tool %s completed OK", whatsapp_sender_id, tc.name)
                except Exception as exc:
                    log.exception("[agent:%s] tool %s raised: %s", whatsapp_sender_id, tc.name, exc)
                    out = json.dumps({"error": str(exc)})
                finally:
                    if on_tool_progress:
                        try:
                            await on_tool_progress("end", tc.name)
                        except Exception:
                            log.debug("on_tool_progress(end) failed", exc_info=True)

                msgs.append(ChatMessage(
                    role="tool",
                    tool_call_id=tc.id,
                    name=tc.name,
                    content=out,
                ))
            continue

        log.info("[agent:%s] no tool calls — generating final response", whatsapp_sender_id)
        final_text = (result.content or "").strip() or \
                     "Let me know a bit more about the role you'd love next."
        break

    if final_text is None:
        log.warning("[agent:%s] hit max tool rounds (%d) without final text", whatsapp_sender_id, rounds)
        final_text = "I'm working through your request — could you tell me a bit more about what you're looking for?"

    log.info("[agent:%s] turn complete — response %.80r", whatsapp_sender_id, final_text)

    msgs.append(ChatMessage(role="assistant", content=final_text))
    try:
        await sessions.append_messages(whatsapp_sender_id, msgs[persist_from:])
    except Exception:
        log.warning("Redis append_messages failed for %s — turn complete but history not saved", whatsapp_sender_id)

    # ── Tag the agent's question topic and update _asked_log ────────────────
    # Runs synchronously — cheap (~ms), and the result feeds the next turn's
    # ConversationState. No LLM, no DB; pure regex + Redis merge.
    try:
        from mitra_api.agent.conversation_state import (
            append_asked,
            load_asked_log,
        )
        current_asked = load_asked_log(asked_log_raw)
        new_asked, tagged_topic = append_asked(
            current_asked,
            assistant_text=final_text,
            turn_idx=len(transcript) // 2 + 1,
        )
        if tagged_topic:
            await sessions.merge_signals(
                whatsapp_sender_id,
                {"_asked_log": [a.to_dict() for a in new_asked]},
            )
            log.info(
                "[agent:%s] tagged agent question — topic=%s (log size=%d)",
                whatsapp_sender_id, tagged_topic, len(new_asked),
            )
    except Exception:
        log.debug("asked-log update failed (non-critical)", exc_info=True)

    # Fire post-turn reflection now that we have the assistant's response
    _final_text_snap = final_text
    async def _run_reflection() -> None:
        try:
            from mitra_api.tools.intelligence import generate_turn_reflection
            reflection = await generate_turn_reflection(
                user_message=_reflection_args["user_text"],
                known_signals=_reflection_args["signals"],
                assistant_response=_final_text_snap,
            )
            if not reflection:
                return
            to_save: dict[str, Any] = {"_reflection": reflection}
            # Promote phase to a first-class signal so other tools can use it
            if reflection.get("phase"):
                to_save["job_search_phase"] = reflection["phase"]
            await _reflection_args["sessions"].merge_signals(
                _reflection_args["session_id"], to_save
            )
            try:
                async with _reflection_args["db_factory"]() as db:
                    await persist_signals(_reflection_args["session_id"], to_save, session=db)
            except Exception:
                log.debug("reflection DB persist failed (non-critical)")
        except Exception:
            log.debug("post-turn reflection failed (non-critical)", exc_info=True)

    asyncio.create_task(_run_reflection(), name=f"reflect-{whatsapp_sender_id}")

    # Build WhatsApp output structures (unchanged interface)
    footer_txt = ""
    segs_for_plain: list[str] | None = None
    if last_search_jobs_payload:
        footer_txt = str(last_search_jobs_payload.get("whatsapp_footer") or "").strip()
        ws = last_search_jobs_payload.get("whatsapp_segments")
        if isinstance(ws, list) and ws:
            segs_for_plain = [str(x) for x in ws]

    native_rows: tuple[InteractiveListRow, ...] = ()
    job_whys: dict[str, str] = {}
    if last_search_jobs_payload:
        native_rows = job_pick_rows_native_list(last_search_jobs_payload.get("jobs") or [])
        for j in (last_search_jobs_payload.get("jobs") or []):
            jid = str(j.get("external_id") or j.get("id") or "")
            why = str(j.get("why") or j.get("summary") or "").strip()
            if jid and why:
                job_whys[f"job_{jid}"] = why
                job_whys[jid] = why

    whats_intro, whats_outro = prelude_and_outro_for_native_list(final_text, footer_txt)
    fallback_parts = whatsapp_outbound_chain(
        assistant_final_text=final_text,
        search_segments=segs_for_plain,
        search_footer=footer_txt or None,
    )

    return AgentTurn(
        history_assistant_text=final_text,
        native_list_rows=native_rows,
        whatsapp_intro=whats_intro,
        whatsapp_outro=whats_outro,
        whatsapp_fallback_plain_parts=tuple(fallback_parts),
        job_whys=job_whys,
        web_research_sources=tuple(web_research_accum),
    )


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _build_tags(job: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    emp = str(job.get("employment") or "").lower()
    if emp == "full_time":
        tags.append("Full-time")
    elif emp == "contract":
        tags.append("Contract")

    remote = str(job.get("remote_policy") or "").lower()
    loc    = str(job.get("location") or "").lower()
    if remote == "remote" or "remote" in loc:
        tags.append("Remote · India" if "india" in loc else "Remote")
    elif remote == "hybrid" or "hybrid" in loc:
        tags.append("Hybrid · BLR" if ("bengaluru" in loc or "bangalore" in loc) else "Hybrid")

    stack = job.get("stack") or []
    if isinstance(stack, list):
        for s in stack:
            if len(tags) >= 3:
                break
            if str(s).strip():
                tags.append(str(s).strip())
    return tags[:3]
