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
    bcc_ops: bool = False,
) -> bool:
    """
    Send a plain-text email via Resend.

    reply_context: generates a tokenised reply-to address so inbound replies
                   route back to the correct conversation.
    bcc_ops:       when True, BCC MITRA_OPS_EMAIL so the company inbox gets
                   a copy. Use for intros, interview confirmations, and other
                   events the operator should see.
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

    ops_email = (s.mitra_ops_email or "").strip()

    payload: dict = {"from": from_addr, "to": [to], "subject": subject, "text": text}

    # BCC ops inbox for visibility on key transactional emails
    # Skip BCC if ops_email is the same as the recipient (avoid duplicate)
    if bcc_ops and ops_email and ops_email != to:
        payload["bcc"] = [ops_email]

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
    elif ops_email:
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

    log.info("email sent to=%s bcc_ops=%s subject=%s", to, bcc_ops, subject)
    return True
