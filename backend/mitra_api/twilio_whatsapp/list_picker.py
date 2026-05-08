"""Twilio WhatsApp native list-picker via Content API (+ optional delete)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

from mitra_api.whatsapp.interactive_native import InteractiveListRow

log = logging.getLogger(__name__)

CONTENT_API = "https://content.twilio.com/v1/Content"


def _items(rows: tuple[InteractiveListRow, ...]) -> list[dict[str, str]]:
    return [{"item": r.title, "description": r.description, "id": r.row_id} for r in rows]


async def create_twilio_list_picker_content(
    *,
    account_sid: str,
    auth_token: str,
    body: str,
    button_label: str,
    rows: tuple[InteractiveListRow, ...],
) -> str | None:
    """Returns Content SID (HX...) or None on failure."""
    friendly = f"mitra_job_list_{uuid.uuid4().hex[:12]}"
    payload: dict[str, Any] = {
        "friendly_name": friendly,
        "language": "en",
        "types": {
            "twilio/list-picker": {
                "body": body[:1024],
                "button": button_label[:20],
                "items": _items(rows),
            },
        },
    }
    auth = (account_sid, auth_token)
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(CONTENT_API, json=payload, auth=auth)
        if resp.status_code >= 400:
            log.error("Twilio Content create failed %s: %s", resp.status_code, resp.text)
            return None
        data = resp.json()
        sid = data.get("sid")
        return str(sid) if sid else None


async def delete_twilio_content_if_possible(
    *,
    content_sid: str,
    account_sid: str,
    auth_token: str,
) -> None:
    auth = (account_sid, auth_token)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(f"{CONTENT_API}/{content_sid}", auth=auth)
        if resp.status_code >= 400 and resp.status_code != 404:
            log.debug("Twilio Content delete %s: %s", resp.status_code, resp.text)


async def send_twilio_native_job_list_message(
    *,
    account_sid: str,
    auth_token: str,
    from_whatsapp: str,
    to_whatsapp: str,
    body: str,
    button_label: str,
    rows: tuple[InteractiveListRow, ...],
) -> bool:
    sid = await create_twilio_list_picker_content(
        account_sid=account_sid,
        auth_token=auth_token,
        body=body,
        button_label=button_label,
        rows=rows,
    )
    if not sid:
        return False

    msgs_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    form = {
        "From": from_whatsapp.strip(),
        "To": to_whatsapp.strip(),
        "ContentSid": sid,
    }
    auth = (account_sid, auth_token)
    ok = False
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(msgs_url, data=form, auth=auth)
            if resp.status_code >= 400:
                log.error("Twilio list send failed %s: %s", resp.status_code, resp.text)
            else:
                ok = True
    finally:
        await delete_twilio_content_if_possible(
            content_sid=sid,
            account_sid=account_sid,
            auth_token=auth_token,
        )

    return ok
