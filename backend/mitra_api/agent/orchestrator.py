"""
mitra_api/agent/orchestrator.py  (production replacement)

Six tools available to the agent
---------------------------------
1. search_jobs              Vector search + LLM reranking against real Postgres jobs
2. remember_candidate_signals  Persist signals to Redis session + Postgres
3. get_salary_benchmark     India startup salary data by role/stage/seniority
4. request_intro            Record intro + prepare founder message
5. check_intro_status       Look up status of a previously sent intro
6. parse_resume             Extract structured data from PDF sent on WhatsApp

Drop-in replacement for the existing orchestrator.py.
All other files (inbound.py, session_store.py, routes, etc.) stay unchanged.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from mitra_api.agent.prompts import SYSTEM_PROMPT
from mitra_api.agent.session_store import AgentSessionStore
from mitra_api.config import Settings, get_settings
from mitra_api.db.engine import get_session_factory
from mitra_api.llm.factory import get_llm_adapter
from mitra_api.llm.types import ChatMessage, ToolDefinition
from mitra_api.tools.candidates import get_signals as get_persisted_signals
from mitra_api.tools.candidates import persist_signals
from mitra_api.tools.intros import get_intro_status, request_intro
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


@dataclass(frozen=True)
class AgentTurn:
    """Result of handling one inbound user message. Unchanged interface."""
    history_assistant_text: str
    native_list_rows: tuple[InteractiveListRow, ...]
    whatsapp_intro: str | None
    whatsapp_outro: tuple[str, ...]
    whatsapp_fallback_plain_parts: tuple[str, ...]


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
            name="request_intro",
            description=(
                "Send a warm introduction from the candidate to a specific founder. "
                "Call when the candidate explicitly asks to be introduced to a role. "
                "You MUST pass the candidate's name, stack, and current role inline — "
                "they are required fields and the intro will not send without them."
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

            return json.dumps({"ok": True, "stored_keys": list(cleaned.keys())}, ensure_ascii=False)

        # ── 3. get_salary_benchmark ───────────────────────────────────────────
        if name == "get_salary_benchmark":
            result = await get_salary_benchmark_async(
                role=str(args.get("role", "backend engineer")),
                stage=str(args.get("stage", "Series A")),
                seniority=str(args.get("seniority", "senior")),
            )
            return json.dumps(result, ensure_ascii=False)

        # ── 4. request_intro ──────────────────────────────────────────────────
        if name == "request_intro":
            # Persist inline signals immediately so the gate check in request_intro
            # finds them in the DB — even if remember_candidate_signals was never called.
            inline: dict[str, Any] = {}
            if args.get("candidate_name"):
                inline["candidate_name"] = args["candidate_name"]
            if args.get("primary_stack"):
                inline["primary_stack"] = args["primary_stack"]
            if args.get("current_role"):
                inline["current_role"] = args["current_role"]
            if args.get("current_company"):
                inline["current_company"] = args["current_company"]

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
                )
            return json.dumps(result, ensure_ascii=False)

        # ── 5. check_intro_status ─────────────────────────────────────────────
        if name == "check_intro_status":
            async with db_factory() as db:
                result = await get_intro_status(
                    candidate_phone=session_id,
                    job_external_id=str(args.get("job_id", "")),
                    session=db,
                )
            return json.dumps(result, ensure_ascii=False)

        # ── 6. parse_resume ───────────────────────────────────────────────────
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

            if name and stack and role:
                stack_str = ", ".join(stack) if isinstance(stack, list) else str(stack)
                return (
                    f"ACTION REQUIRED: Thin intro(s) exist for {items}. "
                    f"Profile already confirmed — name='{name}', stack={stack}, role='{role}', "
                    f"company='{company}'. "
                    f"Call request_intro NOW with these as inline fields. "
                    f"Do NOT ask for confirmation."
                )
            else:
                missing = [k for k in ("candidate_name", "primary_stack", "current_role")
                           if not signals.get(k)]
                return (
                    f"ACTION REQUIRED: Thin intro(s) for {items}. "
                    f"Profile signals not yet saved (missing: {', '.join(missing)}). "
                    f"CRITICAL: If the candidate has shared their name, tech stack, or current role "
                    f"anywhere in this conversation, extract those values RIGHT NOW and call "
                    f"request_intro with candidate_name, primary_stack, current_role, current_company "
                    f"as inline fields — do NOT ask them to repeat information they already gave. "
                    f"Only ask if the info was genuinely never shared."
                )

    except Exception:
        log.exception("_load_weak_intros_note failed for %s", candidate_phone)
        return None


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

    # Build message history
    msgs: list[ChatMessage] = [ChatMessage(role="system", content=SYSTEM_PROMPT)]
    try:
        msgs.extend(await sessions.get_transcript(whatsapp_sender_id))
    except Exception:
        log.warning("Redis get_transcript failed for %s — starting with empty history", whatsapp_sender_id)
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

    # Inject weak-intro nudge — drives proactive strengthening without candidate having to ask
    weak_note = await _load_weak_intros_note(whatsapp_sender_id, db_factory)
    if weak_note:
        msgs.append(ChatMessage(role="system", content=weak_note))

    # Auto-parse PDF resume before the LLM turn so the agent gets structured data,
    # not a raw URL it has to figure out what to do with.
    user_content = user_text.strip()
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

    last_search_jobs_payload: dict[str, Any] | None = None
    final_text: str | None = None
    rounds = 0

    # On the first round, force search_jobs when the message looks like a job request —
    # prevents the model from answering from training knowledge instead of the live DB.
    _job_keywords = ("job", "role", "opening", "recommend", "match", "search", "find", "available",
                     "opportunit", "position", "listing", "what's out", "show me", "suggest",
                     "give me", "what do you have", "any roles", "any jobs")
    _user_lower = user_content.lower()
    _force_first = "search_jobs" if any(k in _user_lower for k in _job_keywords) else None

    log.info(
        "[agent:%s] turn start — model=%s signals=%s force_first=%s msg=%.80r",
        whatsapp_sender_id, s.mitra_llm_model,
        list(known_signals.keys()) if known_signals else [],
        _force_first, user_content,
    )

    while rounds < s.mitra_agent_max_tool_rounds:
        rounds += 1
        _ft = _force_first if rounds == 1 else None
        log.info("[agent:%s] llm round %d — force_tool=%s", whatsapp_sender_id, rounds, _ft)

        result = await adapter.complete(
            model=s.mitra_llm_model,
            messages=msgs,
            tools=tools,
            max_tokens=s.mitra_llm_max_tokens,
            temperature=s.mitra_llm_temperature,
            force_tool=_ft,
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

                try:
                    out = await run_tool(tc.name, parsed)
                    if tc.name == "search_jobs":
                        try:
                            payload = json.loads(out)
                            last_search_jobs_payload = payload
                            picks = payload.get("picks") or []
                            log.info(
                                "[agent:%s] search_jobs returned %d result(s): %s",
                                whatsapp_sender_id, len(picks),
                                [(p.get("title"), p.get("company")) for p in picks[:5]],
                            )
                        except json.JSONDecodeError:
                            log.warning("[agent:%s] search_jobs result was not valid JSON", whatsapp_sender_id)
                    else:
                        log.info("[agent:%s] tool %s completed OK", whatsapp_sender_id, tc.name)
                except Exception as exc:
                    log.exception("[agent:%s] tool %s raised: %s", whatsapp_sender_id, tc.name, exc)
                    out = json.dumps({"error": str(exc)})

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

    # Build WhatsApp output structures (unchanged interface)
    footer_txt = ""
    segs_for_plain: list[str] | None = None
    if last_search_jobs_payload:
        footer_txt = str(last_search_jobs_payload.get("whatsapp_footer") or "").strip()
        ws = last_search_jobs_payload.get("whatsapp_segments")
        if isinstance(ws, list) and ws:
            segs_for_plain = [str(x) for x in ws]

    native_rows: tuple[InteractiveListRow, ...] = ()
    if last_search_jobs_payload:
        native_rows = job_pick_rows_native_list(last_search_jobs_payload.get("jobs") or [])

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
