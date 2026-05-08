import logging
from typing import Any

import httpx

from mitra_api.llm.adapters.base import LLMAdapter
from mitra_api.llm.types import ChatMessage, LLMResult, ToolCall, ToolDefinition

log = logging.getLogger(__name__)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# Models that use max_completion_tokens (not max_tokens) — all o-series and gpt-4.1+ onwards
_MAX_COMPLETION_TOKENS_PREFIXES = ("o1", "o3", "o4", "gpt-4.1", "gpt-4.5", "gpt-5")

# o1 family does not accept a temperature parameter at all
_NO_TEMPERATURE_PREFIXES = ("o1",)


def _token_limit_param(model: str) -> str:
    m = model.lower()
    if any(m.startswith(p) for p in _MAX_COMPLETION_TOKENS_PREFIXES):
        return "max_completion_tokens"
    return "max_tokens"


def _supports_temperature(model: str) -> bool:
    m = model.lower()
    return not any(m.startswith(p) for p in _NO_TEMPERATURE_PREFIXES)


def _to_openai_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            out.append({"role": "system", "content": m.content or ""})
        elif m.role == "user":
            out.append({"role": "user", "content": m.content or ""})
        elif m.role == "assistant":
            d: dict[str, Any] = {"role": "assistant"}
            if m.content:
                d["content"] = m.content
            if m.tool_calls:
                d["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in m.tool_calls
                ]
            out.append(d)
        elif m.role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": m.tool_call_id or "",
                    "content": m.content or "",
                }
            )
    return out


class OpenAIAdapter(LLMAdapter):
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
        payload: dict[str, Any] = {
            "model": model,
            "messages": _to_openai_messages(messages),
            _token_limit_param(model): max_tokens,
        }
        if _supports_temperature(model):
            payload["temperature"] = temperature
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
            payload["parallel_tool_calls"] = True
            if force_tool:
                payload["tool_choice"] = {"type": "function", "function": {"name": force_tool}}

        headers = {"authorization": f"Bearer {self._api_key}", "content-type": "application/json"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(OPENAI_URL, json=payload, headers=headers)
            if resp.status_code >= 400:
                log.error("openai error %s: %s", resp.status_code, resp.text)
                resp.raise_for_status()
            data = resp.json()

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        tool_calls_raw = msg.get("tool_calls") or []
        calls: list[ToolCall] = []
        for c in tool_calls_raw:
            fn = c.get("function") or {}
            calls.append(
                ToolCall(
                    id=str(c.get("id", "")),
                    name=str(fn.get("name", "")),
                    arguments=str(fn.get("arguments") or "{}"),
                )
            )
        usage = data.get("usage")
        return LLMResult(
            content=msg.get("content"),
            tool_calls=calls,
            finish_reason=choice.get("finish_reason"),
            raw_usage=usage if isinstance(usage, dict) else None,
        )
