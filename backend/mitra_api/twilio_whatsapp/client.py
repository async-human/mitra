import base64
import hashlib
import hmac
import logging

import httpx

from mitra_api.config import Settings, get_settings

log = logging.getLogger(__name__)

TWILIO_MESSAGES = "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"


def compute_twilio_signature(full_url: str, post_params: dict[str, str], auth_token: str) -> str:
    """X-Twilio-Signature uses HMAC-SHA1 of URL + sorted key+value pairs (Twilio protocol)."""
    data = full_url + "".join(f"{k}{post_params[k]}" for k in sorted(post_params.keys()))
    mac = hmac.new(auth_token.encode("utf-8"), data.encode("utf-8"), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode("utf-8")


def verify_twilio_request(
    *,
    full_url: str,
    post_params: dict[str, str],
    signature_header: str | None,
    auth_token: str,
) -> bool:
    if not auth_token.strip():
        return False
    if not signature_header:
        return False
    expected = compute_twilio_signature(full_url, post_params, auth_token)
    return hmac.compare_digest(expected, signature_header)


def normalize_twilio_session_id(from_raw: str) -> str:
    """Stable key for AgentSessionStore (E.164 with leading +, digits only)."""
    s = from_raw.strip()
    if s.lower().startswith("whatsapp:"):
        s = s[9:].strip()
    digits = "".join(c for c in s if c.isdigit())
    if not digits:
        return from_raw.strip()
    return f"+{digits}"


async def send_whatsapp_reply(
    *,
    to_whatsapp_from_value: str,
    body: str,
    settings: Settings | None = None,
) -> None:
    """Send outbound WhatsApp via Twilio REST (sandbox or approved sender)."""
    s = settings or get_settings()
    sid = s.twilio_account_sid.strip()
    token = s.twilio_auth_token.strip()
    frm = s.twilio_whatsapp_from.strip()
    if not sid or not token or not frm:
        log.warning("Twilio send skipped: set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM")
        return
    url = TWILIO_MESSAGES.format(account_sid=sid)
    # Twilio accepts x-www-form-urlencoded
    payload = {"From": frm, "To": to_whatsapp_from_value.strip(), "Body": body[:1600]}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, data=payload, auth=(sid, token))

    if resp.status_code == 429:
        try:
            detail = resp.json()
            code   = detail.get("code", "")
            msg    = detail.get("message", "rate limited")
        except Exception:
            code, msg = "", resp.text[:120]
        log.warning(
            "Twilio rate limit (code %s): %s — message NOT delivered to %s",
            code, msg, to_whatsapp_from_value,
        )
        return  # don't raise — the agent turn succeeded, only delivery failed

    if resp.status_code >= 400:
        log.error("Twilio Messages API %s: %s", resp.status_code, resp.text[:300])
        resp.raise_for_status()
