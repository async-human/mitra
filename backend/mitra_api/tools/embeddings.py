"""
mitra_api/tools/embeddings.py

Generates text embeddings for job matching.
Uses Anthropic's voyage-3 model (best for semantic job/candidate matching)
with automatic fallback to OpenAI text-embedding-3-small.

Used by:
  - jobs/admin.py   when a new job is seeded (generate + store embedding)
  - tools/search.py when matching a candidate query to jobs
"""

from __future__ import annotations

import logging
from typing import Literal

import httpx

from mitra_api.config import get_settings

log = logging.getLogger(__name__)

# Which model to use — must match EMBEDDING_DIM in migrations.py
EmbeddingProvider = Literal["voyage", "openai"]

VOYAGE_URL  = "https://api.voyageai.com/v1/embeddings"
OPENAI_URL  = "https://api.openai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3"
OPENAI_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536  # voyage-3 and text-embedding-3-small both output 1536 dims


async def embed_text(text: str, *, provider: EmbeddingProvider | None = None) -> list[float]:
    """
    Embed a single text string. Returns a list of floats.

    Provider priority:
      1. Explicit provider argument
      2. MITRA_EMBEDDING_PROVIDER env var
      3. Auto-detect: voyage if VOYAGE_API_KEY set, else openai
    """
    s = get_settings()

    resolved = provider or getattr(s, "mitra_embedding_provider", None) or _auto_detect(s)

    if resolved == "voyage":
        return await _embed_voyage(text, s)
    return await _embed_openai(text, s)


async def embed_texts(texts: list[str], *, provider: EmbeddingProvider | None = None) -> list[list[float]]:
    """Batch embed multiple strings. More efficient than calling embed_text in a loop."""
    s = get_settings()
    resolved = provider or getattr(s, "mitra_embedding_provider", None) or _auto_detect(s)

    if resolved == "voyage":
        return await _embed_voyage_batch(texts, s)
    return await _embed_openai_batch(texts, s)


def job_embed_text(job: dict) -> str:
    """
    Produce the string that gets embedded for a job.
    Combines the most discriminative fields — company name is included so
    candidate queries naming a specific company match via cosine similarity.
    """
    parts = [
        job.get("title", ""),
        job.get("company", ""),
        job.get("sector", ""),
        job.get("stage", ""),
        " ".join(job.get("stack") or []),
        job.get("summary", ""),
        job.get("location", ""),
    ]
    return " | ".join(p for p in parts if p).strip()


def query_embed_text(query: str, signals: dict) -> str:
    """
    Produce the string that gets embedded for a candidate query.
    Enriches the raw query with stored candidate signals for better matching.
    """
    parts = [query]
    stack = signals.get("primary_stack") or []
    if isinstance(stack, list) and stack:
        parts.append("skills: " + " ".join(stack))
    motivation = signals.get("motivation") or ""
    if motivation:
        parts.append(f"motivation: {motivation}")
    location = signals.get("location_preference") or []
    if isinstance(location, list) and location:
        parts.append("location: " + " ".join(location))
    stage = signals.get("startup_stage_pref") or []
    if isinstance(stage, list) and stage:
        parts.append("stage: " + " ".join(stage))
    return " | ".join(p for p in parts if p)


# ── VOYAGE ────────────────────────────────────────────────────────────────────

async def _embed_voyage(text: str, s) -> list[float]:
    return (await _embed_voyage_batch([text], s))[0]


async def _embed_voyage_batch(texts: list[str], s) -> list[list[float]]:
    key = getattr(s, "voyage_api_key", "") or ""
    if not key.strip():
        raise RuntimeError("VOYAGE_API_KEY not set")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            VOYAGE_URL,
            json={"input": texts, "model": VOYAGE_MODEL},
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]


# ── OPENAI ────────────────────────────────────────────────────────────────────

async def _embed_openai(text: str, s) -> list[float]:
    return (await _embed_openai_batch([text], s))[0]


async def _embed_openai_batch(texts: list[str], s) -> list[list[float]]:
    key = getattr(s, "openai_api_key", "") or ""
    if not key.strip():
        raise RuntimeError("OPENAI_API_KEY not set")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            OPENAI_URL,
            json={"input": texts, "model": OPENAI_MODEL},
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]


def _auto_detect(s) -> EmbeddingProvider:
    if getattr(s, "voyage_api_key", ""):
        return "voyage"
    return "openai"
