"""
mitra_api/tools/search.py

Production job search pipeline — replaces the keyword scoring in orchestrator.py.

Two-stage approach
------------------
Stage 1 — Vector recall (pgvector cosine similarity)
  Embed the candidate query + stored signals, find the top-K most similar
  job embeddings using approximate nearest-neighbour (IVFFlat index).
  Fast, cheap — runs in < 50ms even with thousands of jobs.

Stage 2 — LLM reranking
  Pass the top-K candidates and the full candidate context to Claude.
  Claude reasons about deeper fit signals: career trajectory, motivation
  alignment, stage readiness, dealbreakers. Returns a ranked list with
  a personalised "why this role fits you specifically" note for each.

This is the same architecture used by production recruitment AI systems.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from mitra_api.config import get_settings
from mitra_api.db.models import Job, JobEmbedding
from mitra_api.llm.factory import get_llm_adapter
from mitra_api.llm.types import ChatMessage
from mitra_api.tools.embeddings import EMBEDDING_DIM, embed_text, query_embed_text

log = logging.getLogger(__name__)

# Stage 1: how many candidates to pull from vector search before reranking
VECTOR_RECALL_K = 20
# Stage 2: how many to return to the agent after reranking
RERANK_TOP_N = 5


async def search_jobs(
    *,
    query: str,
    candidate_signals: dict[str, Any],
    session: AsyncSession,
    seniority: str = "unknown",
    location_hint: str = "",
    employment_types: list[str] | None = None,
    company_filter: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Full two-stage job search.

    Args:
        query:             Natural language query from the agent
        candidate_signals: Stored candidate facts from session store
        session:           Async DB session
        seniority:         intern/mid/senior/lead/principal/unknown
        location_hint:     City/country preference
        employment_types:  full_time/contract
        company_filter:    Company name — when set, jobs from that company are
                           always included in the recall pool (explicit user intent).
        limit:             Max results to return (capped at RERANK_TOP_N)

    Returns:
        List of job dicts with added 'why' and 'fit_label' fields.
    """
    limit = min(limit, RERANK_TOP_N)
    has_explicit_intent = bool(company_filter.strip())

    # ── Stage 1: Vector recall ────────────────────────────────────────────────
    embed_query = query_embed_text(query, candidate_signals)
    try:
        query_vec = await embed_text(embed_query)
    except Exception:
        log.exception("Embedding failed — falling back to keyword search")
        return await _keyword_fallback(query, session, limit, company_filter=company_filter)

    candidates = await _vector_recall(
        query_vec=query_vec,
        session=session,
        k=VECTOR_RECALL_K,
        location_hint=location_hint,
        employment_types=employment_types or [],
    )

    # When the candidate explicitly names a company (or specific role), guarantee
    # those jobs appear in the recall pool regardless of vector similarity.
    if has_explicit_intent:
        pinned = await _explicit_lookup(
            session=session,
            company_filter=company_filter,
        )
        if pinned:
            # Merge: pinned jobs first, then fill remaining slots with vector results
            seen_ids: set[int] = {j["id"] for j in pinned}
            merged = pinned + [j for j in candidates if j["id"] not in seen_ids]
            candidates = merged[:VECTOR_RECALL_K]
            log.info(
                "search_jobs: pinned %d jobs for company_filter=%r; pool now %d",
                len(pinned), company_filter, len(candidates),
            )

    if not candidates:
        # Retry once without hard filters to avoid false "no matches"
        # when location/employment constraints are too strict.
        if location_hint or (employment_types and "unknown" not in (employment_types or [])):
            candidates = await _vector_recall(
                query_vec=query_vec,
                session=session,
                k=VECTOR_RECALL_K,
                location_hint="",
                employment_types=[],
            )
        if not candidates:
            return await _keyword_fallback(query, session, limit, company_filter=company_filter)

    if len(candidates) <= limit:
        # Not enough candidates to warrant reranking — add basic fit labels and return
        return _add_fit_labels(candidates, base_pct=88)

    # ── Stage 2: LLM reranking ────────────────────────────────────────────────
    try:
        reranked = await _llm_rerank(
            jobs=candidates,
            query=query,
            signals=candidate_signals,
            seniority=seniority,
            top_n=limit,
            explicit_intent=has_explicit_intent,
        )
        return reranked
    except Exception:
        log.exception("LLM reranking failed — returning vector results directly")
        return _add_fit_labels(candidates[:limit], base_pct=88)


# ── EXPLICIT COMPANY / ROLE LOOKUP ───────────────────────────────────────────

async def _explicit_lookup(
    *,
    session: AsyncSession,
    company_filter: str,
) -> list[dict[str, Any]]:
    """
    Fetch all active jobs that match the explicitly named company.
    Used to guarantee the candidate's stated intent is always in the recall pool.
    """
    sql = """
        SELECT
            j.id,
            j.external_id,
            j.title,
            j.company,
            j.stage,
            j.sector,
            j.location,
            j.remote_policy,
            j.employment,
            j.salary_min_lpa,
            j.salary_max_lpa,
            j.stack,
            j.signals,
            j.summary,
            j.founder_name,
            1.0 AS cosine_similarity
        FROM jobs j
        WHERE j.status = 'active'
          AND j.company ILIKE :company
        LIMIT 10
    """
    result = await session.execute(text(sql), {"company": f"%{company_filter}%"})
    rows = result.mappings().all()
    jobs = []
    for row in rows:
        job = dict(row)
        for field in ("stack", "signals"):
            if isinstance(job.get(field), str):
                try:
                    job[field] = json.loads(job[field])
                except json.JSONDecodeError:
                    job[field] = []
        jobs.append(job)
    return jobs


# ── STAGE 1: VECTOR RECALL ────────────────────────────────────────────────────

async def _vector_recall(
    *,
    query_vec: list[float],
    session: AsyncSession,
    k: int,
    location_hint: str,
    employment_types: list[str],
) -> list[dict[str, Any]]:
    """
    Find top-K jobs by cosine similarity using pgvector.
    Only queries active jobs. Applies optional hard filters before vector search.
    """
    # Build the vector literal for pgvector
    vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

    # Base query: active jobs ordered by cosine distance
    sql = """
        SELECT
            j.id,
            j.external_id,
            j.title,
            j.company,
            j.stage,
            j.sector,
            j.location,
            j.remote_policy,
            j.employment,
            j.salary_min_lpa,
            j.salary_max_lpa,
            j.stack,
            j.signals,
            j.summary,
            j.founder_name,
            (1 - (je.embedding <=> CAST(:vec AS vector))) AS cosine_similarity
        FROM jobs j
        JOIN job_embeddings je ON je.job_id = j.id
        WHERE j.status = 'active'
    """

    params: dict[str, Any] = {"vec": vec_str}

    # Hard filter: location
    if location_hint:
        sql += " AND (j.location ILIKE :loc OR j.remote_policy = 'remote')"
        params["loc"] = f"%{location_hint}%"

    # Hard filter: employment type
    if employment_types and "unknown" not in employment_types:
        placeholders = ", ".join(f":et{i}" for i in range(len(employment_types)))
        sql += f" AND j.employment IN ({placeholders})"
        for i, et in enumerate(employment_types):
            params[f"et{i}"] = et

    sql += " ORDER BY je.embedding <=> CAST(:vec AS vector) LIMIT :k"
    params["k"] = k

    result = await session.execute(text(sql), params)
    rows = result.mappings().all()

    jobs = []
    for row in rows:
        job = dict(row)
        # Parse JSONB fields that come back as strings in some drivers
        for field in ("stack", "signals"):
            if isinstance(job.get(field), str):
                try:
                    job[field] = json.loads(job[field])
                except json.JSONDecodeError:
                    job[field] = []
        jobs.append(job)

    return jobs


# ── STAGE 2: LLM RERANKING ────────────────────────────────────────────────────

_RERANK_SYSTEM = """You are a talent matching engine. Given a candidate profile and a list of jobs,
rank the jobs from best to worst fit for this specific candidate.

For each job you include, write a 1-2 sentence "why" that explains WHY this specific role
fits THIS specific candidate — referencing details from their profile. Be concrete and honest.
Do NOT include a job if it's clearly a poor fit.

Return ONLY a JSON array with this structure (no markdown, no preamble):
[
  {
    "id": "<job id>",
    "rank": 1,
    "fit_pct": 94,
    "why": "Owns payment rails end-to-end — exactly what you said you want after 3 years of maintenance work at Infosys."
  },
  ...
]

fit_pct should reflect genuine fit (60-97 range). Only include jobs where fit_pct >= 70."""

_RERANK_SYSTEM_EXPLICIT = """You are a talent matching engine. Given a candidate profile and a list of jobs,
rank the jobs from best to worst fit for this specific candidate.

The candidate has explicitly asked about specific companies or roles — include ALL jobs from those
companies in your output, even if the fit is partial. Write an honest "why" for each.

Return ONLY a JSON array with this structure (no markdown, no preamble):
[
  {
    "id": "<job id>",
    "rank": 1,
    "fit_pct": 94,
    "why": "Direct match to what you asked for — payments engineering at a funded fintech."
  },
  ...
]

fit_pct should reflect genuine fit (50-97 range). Include all jobs from explicitly requested
companies. For other jobs, only include where fit_pct >= 70."""


async def _llm_rerank(
    *,
    jobs: list[dict[str, Any]],
    query: str,
    signals: dict[str, Any],
    seniority: str,
    top_n: int,
    explicit_intent: bool = False,
) -> list[dict[str, Any]]:
    """
    Ask the LLM to rerank and annotate the vector-recalled jobs.
    Returns at most top_n jobs with personalised 'why' notes and fit percentages.
    """
    s = get_settings()

    # Build candidate context string
    candidate_ctx = f"Query: {query}\nSeniority: {seniority}\n"
    for k, v in signals.items():
        candidate_ctx += f"{k}: {json.dumps(v, ensure_ascii=False)}\n"

    # Slim job list for the reranker prompt (only fields relevant to fit)
    slim_jobs = [
        {
            "id": j.get("external_id") or str(j["id"]),
            "title": j["title"],
            "company": j["company"],
            "stage": j.get("stage") or "",
            "sector": j.get("sector") or "",
            "location": j.get("location") or "",
            "remote": j.get("remote_policy") or "",
            "employment": j.get("employment") or "",
            "salary_lpa": f"{j.get('salary_min_lpa') or '?'}-{j.get('salary_max_lpa') or '?'}",
            "stack": j.get("stack") or [],
            "summary": (j.get("summary") or "")[:200],
        }
        for j in jobs
    ]

    user_msg = (
        f"CANDIDATE PROFILE:\n{candidate_ctx}\n\n"
        f"JOBS TO RANK:\n{json.dumps(slim_jobs, ensure_ascii=False, indent=2)}"
    )

    system_prompt = _RERANK_SYSTEM_EXPLICIT if explicit_intent else _RERANK_SYSTEM

    # Use whichever provider is configured (OpenAI/Anthropic) via shared adapter.
    adapter = get_llm_adapter(s)
    result = await adapter.complete(
        model=s.mitra_llm_model,
        messages=[
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_msg),
        ],
        tools=None,
        max_tokens=1024,
        temperature=0.0,
    )
    raw = (result.content or "").strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()

    ranked: list[dict] = json.loads(raw)
    ranked.sort(key=lambda x: x.get("rank", 99))
    ranked = ranked[:top_n]

    # Map back to full job dicts using external_id or id
    id_to_job = {}
    for j in jobs:
        id_to_job[str(j["id"])] = j
        if j.get("external_id"):
            id_to_job[j["external_id"]] = j

    results = []
    for r in ranked:
        jid = str(r.get("id", ""))
        job = id_to_job.get(jid)
        if not job:
            continue
        enriched = {**job}
        enriched["why"]       = r.get("why", job.get("summary", ""))[:300]
        enriched["fit_label"] = f"{r.get('fit_pct', 88)}% fit"
        enriched["fit_pct"]   = r.get("fit_pct", 88)
        results.append(enriched)

    return results


# ── KEYWORD FALLBACK ──────────────────────────────────────────────────────────

async def _keyword_fallback(
    query: str,
    session: AsyncSession,
    limit: int,
    company_filter: str = "",
) -> list[dict[str, Any]]:
    """Simple ILIKE fallback when embedding fails — better than returning nothing."""
    tokens = [t for t in query.lower().split() if len(t) > 2]
    params: dict[str, Any] = {"lim": limit}

    if company_filter:
        # Explicit company intent — prioritise direct company match
        company_clause = "LOWER(company) LIKE :company"
        params["company"] = f"%{company_filter.lower()}%"
        if tokens:
            token_clause = " OR ".join(
                f"(LOWER(title) LIKE :t{i} OR LOWER(summary) LIKE :t{i} OR LOWER(company) LIKE :t{i})"
                for i in range(len(tokens))
            )
            for i, tok in enumerate(tokens):
                params[f"t{i}"] = f"%{tok}%"
            where = f"({company_clause}) OR ({token_clause})"
        else:
            where = company_clause
        sql = f"SELECT * FROM jobs WHERE status = 'active' AND ({where}) ORDER BY ({company_clause}) DESC LIMIT :lim"
    elif tokens:
        conditions = " OR ".join(
            f"(LOWER(title) LIKE :t{i} OR LOWER(summary) LIKE :t{i} OR LOWER(company) LIKE :t{i})"
            for i in range(len(tokens))
        )
        for i, tok in enumerate(tokens):
            params[f"t{i}"] = f"%{tok}%"
        sql = f"SELECT * FROM jobs WHERE status = 'active' AND ({conditions}) LIMIT :lim"
    else:
        result = await session.execute(
            select(Job).where(Job.status == "active").limit(limit)
        )
        jobs = result.scalars().all()
        return _add_fit_labels(
            [j.__dict__ if hasattr(j, "__dict__") else j for j in jobs],
            base_pct=82,
        )

    result = await session.execute(text(sql), params)
    jobs = [dict(row) for row in result.mappings().all()]
    return _add_fit_labels(jobs, base_pct=82)


def _add_fit_labels(jobs: list[dict], base_pct: int = 88) -> list[dict]:
    for i, job in enumerate(jobs):
        if "fit_label" not in job:
            pct = max(70, base_pct - i * 3)
            job["fit_label"] = f"{pct}% fit"
            job["fit_pct"]   = pct
        if "why" not in job or not job["why"]:
            job["why"] = job.get("summary", "")
    return jobs
