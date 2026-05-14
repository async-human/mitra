"""
Live web search for agent market research (Tavily API).

Used when candidates want fresher / third-party context than Mitra's DB —
salary surveys, news, funding, hiring trends. Requires TAVILY_API_KEY.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from mitra_api.config import Settings

log = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


async def web_market_research(query: str, settings: Settings) -> dict[str, Any]:
    q = (query or "").strip()
    if len(q) < 4:
        return {
            "ok": False,
            "error": "Query too short — pass a specific web search question.",
        }

    key = (settings.tavily_api_key or "").strip()
    if not key:
        return {
            "ok": False,
            "error": (
                "Web market research is not configured on this server "
                "(set TAVILY_API_KEY)."
            ),
            "hint": (
                "Use get_salary_benchmark for India startup salary bands "
                "(Mitra live jobs + curated benchmarks)."
            ),
        }

    depth = settings.mitra_tavily_search_depth
    max_r = max(1, min(int(settings.mitra_market_research_max_results), 10))

    body = {
        "api_key": key,
        "query": q,
        "search_depth": depth,
        "max_results": max_r,
        "include_answer": True,
        "include_raw_content": False,
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(TAVILY_SEARCH_URL, json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        log.warning(
            "Tavily HTTP %s: %s",
            e.response.status_code,
            (e.response.text or "")[:300],
        )
        return {
            "ok": False,
            "error": f"Web search failed (HTTP {e.response.status_code}). Try again later.",
        }
    except Exception:
        log.exception("Tavily search failed")
        return {
            "ok": False,
            "error": "Web search failed unexpectedly. Try again later.",
        }

    answer = (data.get("answer") or "").strip()
    raw_results = data.get("results") or []
    if not isinstance(raw_results, list):
        raw_results = []

    trimmed: list[dict[str, str]] = []
    for r in raw_results[:max_r]:
        if not isinstance(r, dict):
            continue
        title = str(r.get("title") or "")[:400]
        url = str(r.get("url") or "")[:800]
        snippet = str(r.get("content") or "").strip().replace("\n", " ")
        if len(snippet) > 500:
            snippet = snippet[:497] + "…"
        trimmed.append({"title": title, "url": url, "snippet": snippet})

    msg_parts: list[str] = []
    if answer:
        msg_parts.append("Summary (from search index):\n" + answer)
    if trimmed:
        msg_parts.append("Sources:")
        for i, r in enumerate(trimmed, start=1):
            msg_parts.append(
                f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet']}"
            )
    message = "\n\n".join(msg_parts) if msg_parts else "No results returned."

    return {
        "ok": True,
        "query": q,
        "answer": answer or None,
        "results": trimmed,
        "message": message,
        "disclaimer": (
            "Third-party web snippets — verify important facts on the original pages; "
            "not legal or financial advice."
        ),
    }
