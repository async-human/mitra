import hashlib
import hmac
import logging
from typing import Any

import httpx

from mitra_api.config import Settings, get_settings

log = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"


def verify_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not app_secret.strip():
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    got = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, got)


async def send_text_message(*, to_wa_id: str, body: str, settings: Settings | None = None) -> None:
    s = settings or get_settings()
    phone_id = s.whatsapp_phone_number_id.strip()
    token = s.whatsapp_access_token.strip()
    if not phone_id or not token:
        log.warning("WhatsApp send skipped: missing PHONE_NUMBER_ID or ACCESS_TOKEN")
        return
    url = f"{GRAPH_BASE}/{phone_id}/messages"
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_wa_id,
        "type": "text",
        "text": {"body": body[:4096]},
    }
    headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            log.error("whatsapp send failed %s: %s", resp.status_code, resp.text)
            resp.raise_for_status()
