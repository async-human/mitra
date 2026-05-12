import json
import logging
from typing import Any

import httpx

from mitra_api.llm.adapters.base import LLMAdapter
from mitra_api.llm.types import ChatMessage, LLMResult, ToolCall, ToolDefinition

log = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
_CACHE_BETA = "prompt-caching-2024-07-31"


def _to_anthropic_messages(
    messages: list[ChatMessage],
) -> tuple[list[dict[str, Any]] | str, list[dict[str, Any]]]:
    """
    Convert ChatMessage list to Anthropic API format.

    System messages are collected into a content-block array so that
    cache_control can be applied per-block. If no message carries
    cache_control the system value is a plain string (backwards-compatible).

    Returns (system, messages) where system is either a plain string
    (no caching) or a list of content blocks (caching enabled).
    """
    system_blocks: list[dict[str, Any]] = []
    out: list[dict[str, Any]] = []
    pending_tool_results: list[dict[str, Any]] = []

    def flush_tools() -> None:
        nonlocal pending_tool_results
        if not pending_tool_results:
            return
        out.append({"role": "user", "content": pending_tool_results})
        pending_tool_results = []

    for m in messages:
        if m.role == "system":
            if not m.content:
                continue
            block: dict[str, Any] = {"type": "text", "text": m.content}
            if m.cache_control:
                block["cache_control"] = m.cache_control
            system_blocks.append(block)
            continue

        if m.role == "user":
            flush_tools()
            content_block: dict[str, Any] = {"type": "text", "text": m.content or ""}
            if m.cache_control:
                content_block["cache_control"] = m.cache_control
            out.append({"role": "user", "content": [content_block]})
            continue

        if m.role == "assistant":
            flush_tools()
            blocks: list[dict[str, Any]] = []
            if m.content:
                blocks.append({"type": "text", "text": m.content})
            if m.tool_calls:
                for tc in m.tool_calls:
                    try:
                        inp = json.loads(tc.arguments) if tc.arguments.strip() else {}
                    except json.JSONDecodeError:
                        inp = {"_raw": tc.arguments}
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": inp,
                        }
                    )
            out.append({"role": "assistant", "content": blocks})
            continue

        if m.role == "tool":
            pending_tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": m.tool_call_id or "",
                    "content": m.content or "",
                }
            )

    flush_tools()

    # Collapse system blocks to a plain string if none have cache_control
    # (avoids the beta header requirement for callers that don't need caching).
    any_cached = any("cache_control" in b for b in system_blocks)
    if system_blocks and not any_cached:
        system: list[dict[str, Any]] | str = "\n\n".join(
            b["text"] for b in system_blocks
        )
    else:
        system = system_blocks  # array form — may be empty list

    return system, out


class AnthropicAdapter(LLMAdapter):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def complete(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None,
        max_tokens: int,
        temperature: float,
        force_tool: str | None = None,
    ) -> LLMResult:
        system, anth_msgs = _to_anthropic_messages(messages)
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anth_msgs,
        }

        needs_cache_beta = False
        if system:
            payload["system"] = system
            if isinstance(system, list):
                needs_cache_beta = any("cache_control" in b for b in system)

        # Check user/assistant messages for cache_control too
        if not needs_cache_beta:
            for msg in anth_msgs:
                content = msg.get("content")
                if isinstance(content, list):
                    if any("cache_control" in b for b in content):
                        needs_cache_beta = True
                        break

        if tools:
            payload["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]
            if force_tool:
                payload["tool_choice"] = {"type": "tool", "name": force_tool}

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        if needs_cache_beta:
            headers["anthropic-beta"] = _CACHE_BETA

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(ANTHROPIC_URL, json=payload, headers=headers)
            if resp.status_code >= 400:
                log.error("anthropic error %s: %s", resp.status_code, resp.text)
                resp.raise_for_status()
            data = resp.json()

        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []
        for block in data.get("content", []) or []:
            btype = block.get("type")
            if btype == "text":
                text_parts.append(block.get("text") or "")
            elif btype == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=str(block.get("id", "")),
                        name=str(block.get("name", "")),
                        arguments=json.dumps(block.get("input") or {}),
                    )
                )

        usage = data.get("usage")
        if usage and needs_cache_beta:
            log.debug(
                "cache usage — creation: %s, read: %s",
                usage.get("cache_creation_input_tokens", 0),
                usage.get("cache_read_input_tokens", 0),
            )

        return LLMResult(
            content="\n".join(text_parts).strip() or None,
            tool_calls=tool_calls,
            finish_reason=data.get("stop_reason"),
            raw_usage=usage if isinstance(usage, dict) else None,
        )
