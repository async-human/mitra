"""Meta WhatsApp Cloud — interactive list messages."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from mitra_api.config import Settings, get_settings
from mitra_api.whatsapp.interactive_native import InteractiveListRow

log = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"


def _rows_payload(rows: tuple[InteractiveListRow, ...]) -> list[dict[str, str]]:
    return [{"id": r.row_id, "title": r.title, "description": r.description} for r in rows]


async def send_interactive_job_list_message(
    *,
    to_digits: str,
    body_text: str,
    footer_text: str | None,
    button_label: str,
    rows: tuple[InteractiveListRow, ...],
    settings: Settings | None = None,
) -> None:
    """Session message: WhatsApp renders a tap-to-expand list (native UX)."""
    s = settings or get_settings()
    phone_id = s.whatsapp_phone_number_id.strip()
    token = s.whatsapp_access_token.strip()
    if not phone_id or not token or not to_digits.strip():
        log.warning("Meta interactive send skipped (PHONE_NUMBER_ID, TOKEN, or to missing)")
        return
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_digits,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": (body_text or "Your shortlist")[:1024]},
            "action": {
                "button": (button_label or "View picks")[:20],
                "sections": [
                    {"title": "Top matches", "rows": _rows_payload(rows)},
                ],
            },
        },
    }
    if footer_text and footer_text.strip():
        payload["interactive"]["footer"] = {"text": footer_text.strip()[:60]}

    url = f"{GRAPH_BASE}/{phone_id}/messages"
    headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            log.error("Meta interactive send %s: %s", resp.status_code, resp.text)
            resp.raise_for_status()
