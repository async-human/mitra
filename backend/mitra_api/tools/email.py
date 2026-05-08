"""Transactional email via Resend (https://resend.com)."""

from __future__ import annotations

import logging

import httpx

from mitra_api.config import get_settings

log = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


async def send_email(*, to: str, subject: str, text: str) -> bool:
    """Send a plain-text email via Resend. Returns True on success."""
    s = get_settings()
    api_key  = s.resend_api_key.strip()
    from_addr = s.mitra_from_email.strip()

    if not api_key:
        log.warning("email send skipped: RESEND_API_KEY not set")
        return False
    if not from_addr:
        log.warning("email send skipped: MITRA_FROM_EMAIL not set")
        return False

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            RESEND_URL,
            json={"from": from_addr, "to": [to], "subject": subject, "text": text},
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    if resp.status_code >= 400:
        log.error("resend error %s: %s", resp.status_code, resp.text)
        return False

    log.info("email sent to %s (subject: %s)", to, subject)
    return True
