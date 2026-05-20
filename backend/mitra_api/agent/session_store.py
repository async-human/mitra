"""
mitra_api/agent/session_store.py  (updated)

Adds get_signals() method to the ABC and both implementations.
The production orchestrator calls get_signals() to enrich job search
queries with stored candidate facts.

Everything else is unchanged from the previous version.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from mitra_api.config import Settings
from mitra_api.llm.types import ChatMessage

log = logging.getLogger(__name__)


class AgentSessionStore(ABC):

    @abstractmethod
    async def get_transcript(self, sid: str) -> list[ChatMessage]:
        """Prior conversation messages (excludes the current user line)."""

    async def get_transcript_windowed(
        self, sid: str, window: int = 12
    ) -> tuple[list[ChatMessage], bool]:
        """
        Return the most recent `window` turns + a flag indicating older turns exist.
        A "turn" = one user message + one assistant message (2 messages, more with tool calls).
        Always starts at a user-message boundary so we never split a tool-call sequence.
        Returns (windowed_turns, has_older_turns).
        """
        full = await self.get_transcript(sid)
        if len(full) <= window * 2:
            return full, False

        # Start point based on message count, then advance to next user-message boundary
        # so we never cut in the middle of an assistant-tool_calls / tool-result sequence.
        candidate_start = len(full) - window * 2
        for i in range(candidate_start, len(full)):
            if full[i].role == "user":
                candidate_start = i
                break

        has_older = candidate_start > 0
        return full[candidate_start:], has_older

    @abstractmethod
    async def append_messages(self, sid: str, msgs: list[ChatMessage]) -> None:
        """Persist new messages after a completed turn."""

    @abstractmethod
    async def clear_transcript(self, sid: str) -> None:
        """Erase all conversation history for this session (keeps signals intact)."""

    @abstractmethod
    async def merge_signals(self, sid: str, updates: dict[str, Any]) -> None:
        """Shallow-merge candidate facts for this sender."""

    @abstractmethod
    async def get_signals(self, sid: str) -> dict[str, Any]:
        """Return all stored signals for this sender."""

    @abstractmethod
    async def store_wa_link_token(self, token: str, email: str, ttl_seconds: int) -> None:
        """Store a short-lived WhatsApp account-linking token → email mapping."""

    @abstractmethod
    async def consume_wa_link_token(self, token: str) -> str | None:
        """Atomically fetch-and-delete a link token. Returns email or None if expired/missing."""

    async def aclose(self) -> None:
        return


class InMemoryAgentSessionStore(AgentSessionStore):
    def __init__(self) -> None:
        self._signals: dict[str, dict[str, Any]] = {}
        self._history: dict[str, list[ChatMessage]] = {}
        self._wa_tokens: dict[str, str] = {}

    async def get_transcript(self, sid: str) -> list[ChatMessage]:
        return list(self._history.get(sid, []))

    async def append_messages(self, sid: str, msgs: list[ChatMessage]) -> None:
        self._history.setdefault(sid, []).extend(msgs)

    async def clear_transcript(self, sid: str) -> None:
        self._history.pop(sid, None)

    async def merge_signals(self, sid: str, updates: dict[str, Any]) -> None:
        merged = self._signals.setdefault(sid, {})
        for k, v in updates.items():
            merged[str(k)] = v

    async def get_signals(self, sid: str) -> dict[str, Any]:
        return dict(self._signals.get(sid, {}))

    async def store_wa_link_token(self, token: str, email: str, ttl_seconds: int) -> None:
        self._wa_tokens[token.upper()] = email

    async def consume_wa_link_token(self, token: str) -> str | None:
        return self._wa_tokens.pop(token.upper(), None)


class RedisAgentSessionStore(AgentSessionStore):
    def __init__(self, *, client: Any, ttl_seconds: int, key_prefix: str) -> None:
        self._r      = client
        self._ttl    = max(60, ttl_seconds)
        self._pfx    = key_prefix.strip() or "mitra"

    def _msg_key(self, sid: str) -> str:
        return f"{self._pfx}:session:{sid}:msgs"

    def _sig_key(self, sid: str) -> str:
        return f"{self._pfx}:session:{sid}:signals"

    def _wa_link_key(self, token: str) -> str:
        return f"{self._pfx}:walink:{token.upper()}"

    async def get_transcript(self, sid: str) -> list[ChatMessage]:
        raw_list = await self._r.lrange(self._msg_key(sid), 0, -1)
        out: list[ChatMessage] = []
        for raw in raw_list:
            try:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                out.append(ChatMessage.model_validate_json(raw))
            except Exception:
                log.warning("skipped bad transcript chunk sid=%s", sid, exc_info=True)
        return out

    async def append_messages(self, sid: str, msgs: list[ChatMessage]) -> None:
        if not msgs:
            return
        key  = self._msg_key(sid)
        pipe = self._r.pipeline()
        for m in msgs:
            pipe.rpush(key, m.model_dump_json())
        pipe.expire(key, self._ttl)
        await pipe.execute()

    async def clear_transcript(self, sid: str) -> None:
        await self._r.delete(self._msg_key(sid))

    async def merge_signals(self, sid: str, updates: dict[str, Any]) -> None:
        if not updates:
            return
        existing = await self.get_signals(sid)
        existing.update({str(k): v for k, v in updates.items()})
        payload = json.dumps(existing, ensure_ascii=False).encode("utf-8")
        await self._r.set(self._sig_key(sid), payload, ex=self._ttl)

    async def get_signals(self, sid: str) -> dict[str, Any]:
        raw = await self._r.get(self._sig_key(sid))
        if not raw:
            return {}
        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            loaded = json.loads(raw)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            log.warning("corrupted signals blob for sid=%s — returning empty", sid)
            return {}

    async def store_wa_link_token(self, token: str, email: str, ttl_seconds: int) -> None:
        await self._r.set(self._wa_link_key(token), email.encode("utf-8"), ex=ttl_seconds)

    async def consume_wa_link_token(self, token: str) -> str | None:
        raw = await self._r.getdel(self._wa_link_key(token))
        if not raw:
            return None
        return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)

    async def aclose(self) -> None:
        await self._r.aclose()


def build_session_store(settings: Settings) -> AgentSessionStore:
    url = settings.mitra_redis_url.strip()
    if not url:
        log.info("MITRA_REDIS_URL unset — using in-memory sessions (dev mode)")
        return InMemoryAgentSessionStore()

    try:
        import redis.asyncio as redis
        from redis.asyncio.retry import Retry
        from redis.backoff import ExponentialBackoff
        from redis.exceptions import ConnectionError as RedisConnError, TimeoutError as RedisTimeoutError
    except ImportError as exc:
        raise RuntimeError("redis package required when MITRA_REDIS_URL is set") from exc

    retry = Retry(ExponentialBackoff(), retries=3)
    client = redis.from_url(
        url,
        decode_responses=False,
        socket_keepalive=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry=retry,
        retry_on_error=[RedisConnError, RedisTimeoutError, ConnectionResetError],
        health_check_interval=30,
    )
    log.info(
        "Redis sessions: ttl=%ds prefix=%r",
        settings.mitra_session_ttl_seconds,
        settings.mitra_redis_key_prefix,
    )
    return RedisAgentSessionStore(
        client=client,
        ttl_seconds=settings.mitra_session_ttl_seconds,
        key_prefix=settings.mitra_redis_key_prefix,
    )
