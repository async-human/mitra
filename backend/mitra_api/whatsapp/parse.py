import logging
from typing import Any

log = logging.getLogger(__name__)


def extract_incoming_text(body: dict[str, Any]) -> list[tuple[str, str]]:
    """Return list of (from_wa_id, text) for supported inbound message types."""
    out: list[tuple[str, str]] = []
    entries = body.get("entry") or []
    for entry in entries:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            messages = value.get("messages") or []
            for msg in messages:
                from_id = str(msg.get("from") or "")
                if not from_id:
                    continue
                mtype = msg.get("type")
                if mtype == "text":
                    text_obj = msg.get("text") or {}
                    t = str(text_obj.get("body") or "").strip()
                    if t:
                        out.append((from_id, t))
                elif mtype == "button":
                    btn = msg.get("button") or {}
                    t = str(btn.get("text") or "").strip()
                    if t:
                        out.append((from_id, t))
                elif mtype == "interactive":
                    # User tapped a list-reply or button-reply row
                    interactive = msg.get("interactive") or {}
                    itype = interactive.get("type")
                    if itype == "list_reply":
                        reply = interactive.get("list_reply") or {}
                        t = str(reply.get("title") or reply.get("id") or "").strip()
                    elif itype == "button_reply":
                        reply = interactive.get("button_reply") or {}
                        t = str(reply.get("title") or reply.get("id") or "").strip()
                    else:
                        t = ""
                    if t:
                        out.append((from_id, t))
    return out
