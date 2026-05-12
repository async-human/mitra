"""
mitra_api/founder/job_builder.py

Autonomous founder job-posting agent.

Flow:
  1. Founder sends free text OR uploads a JD document
  2. Agent extracts all job fields + generates a rich candidate-facing summary
  3. If anything critical is missing → asks ONE follow-up question (max)
  4. Once enough data: returns stage="confirming" with job_preview
  5. Founder confirms → job created in DB + portal URL returned (stage="posted")
"""

from __future__ import annotations

import json
import logging
import re
import secrets as _secrets
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from mitra_api.agent.session_store import AgentSessionStore, build_session_store
from mitra_api.config import Settings, get_settings
from mitra_api.founder.jd_parser import extract_jd_signals, extract_jd_text
from mitra_api.llm.factory import get_llm_adapter
from mitra_api.llm.types import ChatMessage, ToolDefinition

log = logging.getLogger(__name__)

router = APIRouter(prefix="/founder/job-builder", tags=["founder-job-builder"])

_SESSION_PREFIX = "jb"  # distinct from "founder" (onboarding) sessions

_store: AgentSessionStore | None = None


def _get_store(settings: Settings) -> AgentSessionStore:
    global _store
    if _store is None:
        _store = build_session_store(settings)
    return _store


def _sid(session_id: str) -> str:
    return f"{_SESSION_PREFIX}:{session_id}"


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are Mitra's autonomous job-posting assistant. Help founders post a role with zero friction.

## GROUND RULE — NEVER INVENT DATA
Only extract what is EXPLICITLY written in the founder's message or the uploaded JD text.
Never use your training knowledge to fill in missing fields (salary, experience, stage, funding, headcount, etc.).
If a field is not present in the provided text, leave it null and ask the founder for it.
Showing invented data is worse than showing nothing.

## YOUR FLOW

1. **Intake**: Founder shares text or uploads a JD. Extract every field that is explicitly present.
2. **Follow-up**: After intake, ask for any important fields missing from the JD — especially salary range and experience range. Combine into one natural question: e.g. "What's the salary range and experience level you're targeting?" Don't ask about stage or sector — they're optional.
3. **Generate summary**: ALWAYS write a `summary` from the JD content — 2-3 sentences, candidate-facing, focused on impact and growth. Never skip this.
4. **Mark ready**: Set `ready: true` only when you have title + company + salary range + experience range + at least 2 other fields. If salary or experience are still missing, stay in collecting stage and ask.
5. **Handle edits**: If the founder asks to change something, extract the correction, update the job, set `ready: true` again.

## EXTRACTION RULES

- `stack`: ALWAYS return as an array of strings e.g. ["Python", "FastAPI", "PostgreSQL"]. Never a comma string.
- `salary_min_lpa` / `salary_max_lpa`: integers only. "25–35 LPA" → min=25, max=35. **Null if not explicitly stated in the text — do not estimate or guess.**
- `exp_min_yrs` / `exp_max_yrs`: integer years. "6-11 Yrs" → min=6, max=11. "5+ years" → min=5, max=null. **Null if not explicitly stated — do not estimate.**
- `remote_policy`: ONLY "remote", "hybrid", or "onsite". Infer only from explicit wording in the text ("work from home", "hybrid schedule", etc.).
- `employment`: ONLY "full_time", "contract", or "part_time". Default to "full_time" when unspecified.
- `sector`: infer from the role/company description — e.g. "Fintech", "Data & Analytics", "HealthTech", "B2B SaaS". This is the one field where reasonable inference is acceptable.
- `stage`: extract ONLY if explicitly stated in the JD (e.g. "Series B startup"). Do NOT infer from the company name or your knowledge of the company.
- `summary`: mandatory — synthesise 2-3 sentences from the JD about what the engineer will build, the impact, and why it's worth joining.
- `responsibilities`: all bullets from "Key Responsibilities / What You'll Do" as a string array. Max 8.
- `requirements`: all bullets from "Required Skills / Qualifications / Experience" as a string array. Max 10.
- `nice_to_have`: all bullets from "Preferred / Nice to Have / Bonus" as a string array. Max 6.

## TONE

Warm, efficient, founder-first. Confirm what you found, ask clearly about what's missing. No fluff."""

# ── Tool definition ───────────────────────────────────────────────────────────

_BUILD_TOOL = ToolDefinition(
    name="build_job",
    description="Extract and structure job data from the founder's input. Call on EVERY turn.",
    parameters={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Reply to the founder (2-3 sentences max). Confirm what was parsed, ask only what's missing.",
            },
            "job": {
                "type": "object",
                "description": "ALL job fields extracted so far — always include previously known values.",
                "properties": {
                    "title":          {"type": "string",  "description": "Job title verbatim"},
                    "company":        {"type": "string",  "description": "Company name"},
                    "stage":          {"type": "string",  "description": "Funding stage"},
                    "sector":         {"type": "string",  "description": "Industry vertical"},
                    "location":       {"type": "string",  "description": "City or 'Remote'"},
                    "remote_policy":  {"type": "string",  "enum": ["remote", "hybrid", "onsite"]},
                    "employment":     {"type": "string",  "enum": ["full_time", "contract", "part_time"]},
                    "salary_min_lpa":    {"type": "integer", "description": "Min salary in LPA"},
                    "salary_max_lpa":    {"type": "integer", "description": "Max salary in LPA"},
                    "exp_min_yrs":       {"type": "integer", "description": "Min years of experience required"},
                    "exp_max_yrs":       {"type": "integer", "description": "Max years of experience"},
                    "stack":             {"type": "array",   "items": {"type": "string"}, "description": "Primary technical skills as array"},
                    "summary":           {"type": "string",  "description": "2-3 sentence candidate-facing role summary"},
                    "responsibilities":  {"type": "array",   "items": {"type": "string"}, "description": "Key responsibilities bullet points, max 8"},
                    "requirements":      {"type": "array",   "items": {"type": "string"}, "description": "Required skills and experience bullets, max 10"},
                    "nice_to_have":      {"type": "array",   "items": {"type": "string"}, "description": "Preferred/nice-to-have qualifications, max 6"},
                },
            },
            "ready": {
                "type": "boolean",
                "description": "True ONLY when title + company + salary_min_lpa + exp_min_yrs + 2 more fields are all present and explicitly sourced from the JD or confirmed by the founder. Stay false and ask if salary or experience are missing.",
            },
            "quick_replies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 short option chips. [] for open-ended questions.",
            },
        },
        "required": ["message", "job", "ready"],
    },
)

# ── Helpers ───────────────────────────────────────────────────────────────────

_CONFIRM_PHRASES = (
    "yes", "post it", "post", "looks good", "perfect", "go ahead",
    "great", "approved", "publish", "ok", "okay", "yep", "sure",
    "do it", "proceed", "confirm", "submit", "correct", "right",
    "all good", "good to go", "that's right", "let's go", "ship it",
)


def _is_confirmation(text: str) -> bool:
    t = text.lower().strip()
    return any(phrase in t for phrase in _CONFIRM_PHRASES) and len(t) < 80


def _parse_salary(raw: str) -> tuple[int | None, int | None]:
    nums = [int(n) for n in re.findall(r"\d+", str(raw))]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def _merge_job(base: dict, update: dict) -> dict:
    """Merge update into base, only overwriting with non-empty values."""
    result = dict(base)
    for k, v in update.items():
        if v is not None and v != "" and v != []:
            result[k] = v
    return result


async def _create_job(job: dict, auth_email: str | None, session_id: str) -> tuple[int, str, str, str | None, str | None]:
    """Create a Job record in DB. Returns (job_id, portal_url, company, sector, location). Idempotent."""
    from sqlalchemy import select
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Job as JobModel, JobStatus
    from mitra_api.jobs.admin import _generate_and_store_embedding

    title   = (job.get("title") or "").strip()
    company = (job.get("company") or "").strip()
    if not title:
        raise ValueError("job title is required")
    if not company:
        raise ValueError("company name is required")

    external_id = f"jb:{session_id}"
    factory = get_session_factory()

    async with factory() as db:
        existing = (await db.execute(
            select(JobModel).where(JobModel.external_id == external_id)
        )).scalar_one_or_none()

        if existing:
            settings = get_settings()
            portal_url = f"{settings.mitra_web_base_url.rstrip('/')}/founder/portal?token={existing.founder_access_token}"
            return existing.id, portal_url, company, job.get("sector"), job.get("location")

        sal_min = job.get("salary_min_lpa")
        sal_max = job.get("salary_max_lpa")
        if isinstance(sal_min, str):
            sal_min, sal_max = _parse_salary(sal_min)

        stack = job.get("stack") or []
        if isinstance(stack, str):
            stack = [s.strip() for s in stack.split(",") if s.strip()]

        # Structured fields stored in signals JSONB
        extra_signals: dict = {}
        for key in ("exp_min_yrs", "exp_max_yrs", "responsibilities", "requirements", "nice_to_have"):
            val = job.get(key)
            if val is not None and val != [] and val != "":
                extra_signals[key] = val

        new_job = JobModel(
            external_id=external_id,
            status=JobStatus.active,
            title=title,
            company=company,
            stage=job.get("stage"),
            sector=job.get("sector"),
            location=job.get("location"),
            remote_policy=job.get("remote_policy"),
            employment=job.get("employment") or "full_time",
            salary_min_lpa=int(sal_min) if sal_min is not None else None,
            salary_max_lpa=int(sal_max) if sal_max is not None else None,
            stack=stack or None,
            signals=extra_signals or None,
            summary=job.get("summary"),
            founder_email=auth_email,
            founder_access_token=_secrets.token_urlsafe(32),
        )
        db.add(new_job)
        await db.flush()

        await _generate_and_store_embedding(new_job, db)
        await db.commit()
        log.info("job_builder: created job id=%d '%s' @ '%s'", new_job.id, title, company)

        try:
            from mitra_api.tools.notifications import notify_matching_candidates_bg
            await notify_matching_candidates_bg(new_job.id)
        except Exception:
            log.warning("job_builder: notify_matching_candidates_bg failed (non-critical)")

        settings = get_settings()
        portal_url = f"{settings.mitra_web_base_url.rstrip('/')}/founder/portal?token={new_job.founder_access_token}"
        return new_job.id, portal_url, company, job.get("sector"), job.get("location")


# ── Schemas ───────────────────────────────────────────────────────────────────

class JobBuilderChatRequest(BaseModel):
    session_id: str       = Field(..., min_length=1, max_length=200)
    message:    str       = Field(default="", max_length=4000)
    auth_email: str | None = Field(default=None)


class JobBuilderChatResponse(BaseModel):
    reply:        str
    stage:        str            # "collecting" | "confirming" | "posted"
    job_preview:  dict | None = None
    portal_url:   str | None = None
    quick_replies: list[str] = []


# ── LLM turn helper ───────────────────────────────────────────────────────────

async def _run_llm_turn(
    *,
    user_content: str,
    transcript: list[ChatMessage],
    current_job: dict,
    settings: Settings,
    store: AgentSessionStore,
    sid: str,
    is_init: bool,
    persist_from_idx: int,
    msgs: list[ChatMessage],
) -> tuple[str, dict, bool, list[str]]:
    """Run one LLM turn. Returns (reply, extracted_job, ready, quick_replies)."""
    adapter = get_llm_adapter(settings)

    result = await adapter.complete(
        model=settings.mitra_llm_model,
        messages=msgs,
        tools=[_BUILD_TOOL],
        max_tokens=settings.mitra_llm_max_tokens,
        temperature=settings.mitra_llm_temperature,
        force_tool="build_job",
    )

    build_call = next(
        (tc for tc in (result.tool_calls or []) if tc.name == "build_job"), None
    )

    reply        = ""
    extracted    = {}
    ready        = False
    quick_replies: list[str] = []

    if build_call:
        try:
            args = json.loads(build_call.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        reply         = str(args.get("message") or "").strip()
        extracted     = args.get("job") or {}
        ready         = bool(args.get("ready", False))
        quick_replies = [str(r) for r in (args.get("quick_replies") or [])[:3] if r]

    if not reply:
        reply = "Could you tell me more about the role?"

    # Persist transcript
    assistant_msg = ChatMessage(role="assistant", content=reply)
    if is_init:
        await store.append_messages(sid, [ChatMessage(role="user", content="[start]"), assistant_msg])
    else:
        await store.append_messages(sid, msgs[persist_from_idx:] + [assistant_msg])

    return reply, extracted, ready, quick_replies


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@router.post("/chat", response_model=JobBuilderChatResponse)
async def job_builder_chat(
    body: JobBuilderChatRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> JobBuilderChatResponse:
    store = _get_store(settings)
    sid   = _sid(body.session_id)
    is_init = not body.message.strip()

    signals     = await store.get_signals(sid)
    transcript  = await store.get_transcript(sid)
    current_stage = signals.get("_stage", "collecting")
    current_job   = json.loads(signals["_job"]) if signals.get("_job") else {}

    # ── Already posted ────────────────────────────────────────────────────────
    if current_stage == "posted":
        return JobBuilderChatResponse(
            reply="Your role is already live! Check your portal to track incoming candidates.",
            stage="posted",
            job_preview=current_job,
            portal_url=signals.get("_portal_url"),
        )

    # ── Confirmation → create job ─────────────────────────────────────────────
    if current_stage == "confirming" and not is_init and _is_confirmation(body.message.strip()):
        try:
            from mitra_api.founder.company_enricher import enrich_company
            job_id, portal_url, _company, _sector, _location = await _create_job(current_job, body.auth_email, body.session_id)
            background_tasks.add_task(
                enrich_company,
                company_name=_company,
                sector=_sector,
                location=_location,
                job_id=job_id,
            )
            log.info("job_builder: company enrichment queued for job_id=%d company=%r", job_id, _company)
            await store.merge_signals(sid, {"_stage": "posted", "_portal_url": portal_url})
            await store.append_messages(sid, [
                ChatMessage(role="user",      content=body.message.strip()),
                ChatMessage(role="assistant", content="Role posted!"),
            ])
            return JobBuilderChatResponse(
                reply="Your role is now live! Mitra will start sending you matched candidates shortly. Here's your founder portal:",
                stage="posted",
                job_preview=current_job,
                portal_url=portal_url,
            )
        except ValueError as e:
            return JobBuilderChatResponse(
                reply=f"Almost there — I still need the {e}. Could you share that?",
                stage="confirming",
                job_preview=current_job,
            )
        except Exception:
            log.exception("job_builder: failed to create job for session %s", body.session_id)
            return JobBuilderChatResponse(
                reply="Something went wrong while posting. Please try again.",
                stage="confirming",
                job_preview=current_job,
                quick_replies=["Try again"],
            )

    # ── Normal LLM turn ───────────────────────────────────────────────────────
    msgs: list[ChatMessage] = [ChatMessage(role="system", content=_SYSTEM_PROMPT)]
    msgs.extend(transcript)
    if current_job:
        msgs.append(ChatMessage(
            role="system",
            content="Job fields collected so far: " + json.dumps(current_job, ensure_ascii=False),
        ))

    user_content = (
        "[CONVERSATION START — greet the founder, explain you'll help post a role in minutes, "
        "ask them to paste the job description or upload a JD file.]"
        if is_init else body.message.strip()
    )
    msgs.append(ChatMessage(role="user", content=user_content))
    persist_from = len(msgs) - 1

    reply, extracted, ready, quick_replies = await _run_llm_turn(
        user_content=user_content,
        transcript=transcript,
        current_job=current_job,
        settings=settings,
        store=store,
        sid=sid,
        is_init=is_init,
        persist_from_idx=persist_from,
        msgs=msgs,
    )

    merged_job = _merge_job(current_job, extracted)
    new_stage  = "confirming" if ready else "collecting"

    await store.merge_signals(sid, {"_stage": new_stage, "_job": json.dumps(merged_job)})

    return JobBuilderChatResponse(
        reply=reply,
        stage=new_stage,
        job_preview=merged_job if new_stage == "confirming" else None,
        quick_replies=quick_replies,
    )


# ── Upload endpoint ───────────────────────────────────────────────────────────

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXT    = {".pdf", ".docx", ".doc"}

_JD_KEY_MAP: dict[str, str | None] = {
    "role_title":     "title",
    "company_name":   "company",
    "salary_range":   None,   # special: parse into min/max
    "location":       "location",
    "stage":          "stage",
    "sector":         "sector",
    "stack":          "stack",
    "why_join":       None,   # folded into summary
    "first_90_days":  None,   # folded into summary
    "culture_signal": None,
    "dealbreaker":    None,
}


def _map_jd_signals(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert jd_parser signal keys → job_builder field keys."""
    out: dict[str, Any] = {}

    for k, v in raw.items():
        if k == "salary_range" and v:
            lo, hi = _parse_salary(str(v))
            if lo is not None:
                out["salary_min_lpa"] = lo
            if hi is not None:
                out["salary_max_lpa"] = hi

        elif k == "stack" and v:
            parts = str(v).split(",")
            out["stack"] = [s.strip() for s in parts if s.strip()]

        elif k in _JD_KEY_MAP:
            mapped = _JD_KEY_MAP[k]
            if mapped:
                out[mapped] = str(v)

        elif k in ("remote_policy", "employment", "summary", "sector", "stage", "location"):
            out[k] = str(v)

    # Build summary from why_join + first_90_days if not already extracted
    summary_parts = []
    if raw.get("why_join"):
        summary_parts.append(str(raw["why_join"]))
    if raw.get("first_90_days"):
        summary_parts.append(f"In the first 90 days: {raw['first_90_days']}")
    if summary_parts and not out.get("summary"):
        out["summary"] = " ".join(summary_parts)

    # Infer remote_policy from location
    if not out.get("remote_policy") and out.get("location"):
        loc = str(out["location"]).lower()
        if "remote" in loc:
            out["remote_policy"] = "remote"
        elif "hybrid" in loc:
            out["remote_policy"] = "hybrid"
        elif loc:
            out["remote_policy"] = "onsite"

    return out


@router.post("/upload", response_model=JobBuilderChatResponse)
async def job_builder_upload(
    session_id: str    = Form(...),
    file: UploadFile   = File(...),
    auth_email: str    = Form(default=""),
    settings: Settings = Depends(get_settings),
) -> JobBuilderChatResponse:
    """Accept a PDF or DOCX JD, extract fields, run LLM enrichment, return chat response."""
    filename = file.filename or ""
    ext = ("." + filename.lower().rsplit(".", 1)[-1]) if "." in filename else ""
    if ext not in _ALLOWED_EXT:
        raise HTTPException(400, "Only PDF and Word (.docx / .doc) files are supported.")

    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Uploaded file is empty.")
    if len(raw) > _MAX_FILE_BYTES:
        raise HTTPException(413, "File too large — maximum 10 MB.")

    text = await extract_jd_text(raw, filename)
    if not text or len(text) < 30:
        raise HTTPException(422, "Could not extract readable text from the file.")

    jd_signals  = await extract_jd_signals(text, settings)
    extracted   = _map_jd_signals(jd_signals)

    store = _get_store(settings)
    sid   = _sid(session_id)

    signals     = await store.get_signals(sid)
    transcript  = await store.get_transcript(sid)
    current_job = json.loads(signals["_job"]) if signals.get("_job") else {}
    merged_job  = _merge_job(current_job, extracted)

    # Truncate JD text conservatively to keep the prompt within token budget
    jd_snippet = text[:7000] if len(text) > 7000 else text
    pre_meta   = json.dumps({k: v for k, v in extracted.items() if v}, ensure_ascii=False)

    user_content = (
        f"[Founder uploaded JD file: '{filename}'.\n\n"
        f"FULL JD TEXT:\n{jd_snippet}\n\n"
        f"Pre-extracted metadata (use as a seed; verify every value against the full text above before using): {pre_meta}\n\n"
        "CRITICAL: Extract ONLY what is explicitly written in the JD text above. "
        "Do NOT use your training knowledge to fill in salary, experience range, funding stage, or any numeric field — "
        "set them null if not stated in the text and ask the founder instead.\n\n"
        "Extract into build_job: title, company, location, remote_policy, employment (default full_time), "
        "exp_min_yrs / exp_max_yrs (null if not explicitly in text), "
        "salary_min_lpa / salary_max_lpa (null if not explicitly in text), "
        "stack (array of technical skills from the JD), sector (infer from role/company description), "
        "stage (ONLY if explicitly stated in the JD — otherwise null), "
        "summary (2-3 sentences from the JD content), "
        "responsibilities (ALL bullets from Key Responsibilities / What You'll Do), "
        "requirements (ALL bullets from Required Skills / Qualifications / Experience), "
        "nice_to_have (ALL bullets from Preferred / Nice to Have / Bonus). "
        "Set ready=false and ask for salary range + experience range if either is missing from the JD.]"
    )

    msgs: list[ChatMessage] = [ChatMessage(role="system", content=_SYSTEM_PROMPT)]
    msgs.extend(transcript)
    if merged_job:
        msgs.append(ChatMessage(
            role="system",
            content="Job fields collected so far: " + json.dumps(merged_job, ensure_ascii=False),
        ))
    msgs.append(ChatMessage(role="user", content=user_content))
    persist_from = len(msgs) - 1

    reply, llm_job, ready, quick_replies = await _run_llm_turn(
        user_content=user_content,
        transcript=transcript,
        current_job=merged_job,
        settings=settings,
        store=store,
        sid=sid,
        is_init=not transcript,
        persist_from_idx=persist_from,
        msgs=msgs,
    )

    final_job = _merge_job(merged_job, llm_job)
    new_stage = "confirming" if ready else "collecting"

    await store.merge_signals(sid, {"_stage": new_stage, "_job": json.dumps(final_job)})

    # Override transcript anchor to show filename
    await store.append_messages(sid, [ChatMessage(role="user", content=f"[Uploaded: {filename}]")])

    return JobBuilderChatResponse(
        reply=reply,
        stage=new_stage,
        job_preview=final_job if new_stage == "confirming" else None,
        quick_replies=quick_replies,
    )
