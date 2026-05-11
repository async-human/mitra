"""
mitra_api/email_reply/token_store.py

Stores one-time reply tokens in Redis so inbound emails can be matched
back to their conversation context.

Key pattern : email_reply:{token} -> JSON context dict
TTL         : 30 days (same as session TTL)
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

log = logging.getLogger(__name__)

_TTL = 60 * 60 * 24 * 30  # 30 days


async def store_reply_token(context: dict[str, Any]) -> str | None:
    """
    Persist reply context keyed by a random hex token.
    Returns the token string, or None if Redis is not configured.
    """
    from mitra_api.config import get_settings
    s = get_settings()
    if not s.mitra_redis_url:
        return None

    import redis.asyncio as aioredis
    token = uuid.uuid4().hex
    key   = f"email_reply:{token}"
    try:
        r = aioredis.from_url(s.mitra_redis_url, decode_responses=True)
        await r.setex(key, _TTL, json.dumps(context))
        await r.aclose()
        log.debug("stored reply token %s context=%s", token, context)
        return token
    except Exception:
        log.exception("store_reply_token failed")
        return None


async def get_reply_context(token: str) -> dict[str, Any] | None:
    """Look up and return reply context by token. Returns None if not found."""
    from mitra_api.config import get_settings
    s = get_settings()
    if not s.mitra_redis_url:
        return None

    import redis.asyncio as aioredis
    key = f"email_reply:{token}"
    try:
        r    = aioredis.from_url(s.mitra_redis_url, decode_responses=True)
        data = await r.get(key)
        await r.aclose()
        if data:
            return json.loads(data)
        return None
    except Exception:
        log.exception("get_reply_context failed for token=%s", token)
        return None
