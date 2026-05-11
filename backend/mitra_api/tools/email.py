"""Transactional email via Resend (https://resend.com)."""

from __future__ import annotations

import logging

import httpx

from mitra_api.config import get_settings

log = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


async def send_email(
    *,
    to: str,
    subject: str,
    text: str,
    reply_context: dict | None = None,
) -> bool:
    """
    Send a plain-text email via Resend.

    If reply_context is provided, a unique reply token is generated and
    stored in Redis. The reply-to address is set to reply+TOKEN@domain so
    inbound replies are routed back to the correct agent conversation.
    """
    s         = get_settings()
    api_key   = s.resend_api_key.strip()
    from_addr = s.mitra_from_email.strip()

    if not api_key:
        log.warning("email send skipped: RESEND_API_KEY not set")
        return False
    if not from_addr:
        log.warning("email send skipped: MITRA_FROM_EMAIL not set")
        return False

    payload: dict = {"from": from_addr, "to": [to], "subject": subject, "text": text}

    # Build reply-to: tokenised address if context given, else ops inbox
    reply_to_addr: str | None = None
    if reply_context:
        try:
            from mitra_api.email_reply.token_store import store_reply_token
            token = await store_reply_token(reply_context)
            if token:
                domain        = from_addr.split("@")[-1] if "@" in from_addr else "mitralabs.co"
                reply_to_addr = f"reply+{token}@{domain}"
        except Exception:
            log.debug("reply token generation failed (non-critical)")

    if reply_to_addr:
        payload["reply_to"] = [reply_to_addr]
    else:
        ops_email = (s.mitra_ops_email or "").strip()
        if ops_email:
            payload["reply_to"] = [ops_email]

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            RESEND_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    if resp.status_code >= 400:
        log.error("resend error %s: %s", resp.status_code, resp.text)
        return False

    log.info("email sent to %s (subject: %s)", to, subject)
    return True
