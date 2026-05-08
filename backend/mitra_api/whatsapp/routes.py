import json
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response

from mitra_api.agent.session_store import AgentSessionStore
from mitra_api.config import Settings, get_settings
from mitra_api.inbound import run_agent_reply
from mitra_api.whatsapp.client import send_text_message, verify_signature
from mitra_api.whatsapp.parse import extract_incoming_text

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/whatsapp", tags=["whatsapp"])


def get_session_store() -> AgentSessionStore:
    from mitra_api.main import session_store

    return session_store


@router.get("")
async def verify_webhook(
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
    settings: Settings = Depends(get_settings),
) -> Response:
    if hub_mode != "subscribe":
        raise HTTPException(status_code=403, detail="invalid mode")
    if not settings.whatsapp_verify_token or hub_verify_token != settings.whatsapp_verify_token:
        raise HTTPException(status_code=403, detail="invalid verify token")
    return Response(content=hub_challenge or "", media_type="text/plain")


@router.post("")
async def receive_webhook(
    request: Request,
    background: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[AgentSessionStore, Depends(get_session_store)],
) -> dict[str, str]:
    raw = await request.body()
    sig = request.headers.get("x-hub-signature-256")
    if not verify_signature(raw, sig, settings.whatsapp_app_secret):
        raise HTTPException(status_code=403, detail="invalid signature")

    try:
        body = json.loads(raw.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="invalid json") from exc

    for from_id, text in extract_incoming_text(body):
        fid = from_id

        async def send(msg: str, wa_id: str = fid) -> None:
            await send_text_message(to_wa_id=wa_id, body=msg, settings=settings)

        background.add_task(
            run_agent_reply,
            sender_id=fid,
            user_text=text,
            sessions=store,
            send_plain_text=send,
            settings=settings,
            graph_recipient_digits=fid,
            twilio_destination=None,
        )

    return {"status": "ok"}
