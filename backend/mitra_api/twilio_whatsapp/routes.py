"""Twilio Programmable Messaging (WhatsApp) webhook."""

import logging
import re
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from mitra_api.agent.session_store import AgentSessionStore
from mitra_api.config import Settings, get_settings
from mitra_api.inbound import run_agent_reply
from mitra_api.twilio_whatsapp.client import (
    normalize_twilio_session_id,
    send_whatsapp_reply,
    verify_twilio_request,
)

log = logging.getLogger(__name__)

_YES_PATTERN = re.compile(
    r"^(yes|yeah|yep|sure|ok|okay|send it|yes send it|go ahead)[\s!.]*$", re.I
)

router = APIRouter(prefix="/webhook/twilio/whatsapp", tags=["twilio-whatsapp"])


def get_session_store() -> AgentSessionStore:
    from mitra_api.main import session_store

    return session_store


async def flat_form_to_str_dict(form) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in form.multi_items():
        if isinstance(value, str):
            out[str(key)] = value
        else:
            try:
                raw = await value.read()
                out[str(key)] = raw.decode(errors="replace") if isinstance(raw, bytes) else str(raw)
            except Exception:
                out[str(key)] = ""
    return out


def _signature_url(request: Request, settings: Settings) -> str:
    configured = settings.mitra_twilio_webhook_url.strip()
    if configured:
        return configured.rstrip("/")
    forwarded_proto = request.headers.get("x-forwarded-proto")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    proto = (forwarded_proto.split(",")[0].strip() if forwarded_proto else "") or request.url.scheme
    path_qs = request.url.path
    if request.url.query:
        path_qs += f"?{request.url.query}"
    return f"{proto}://{host}{path_qs}"


@router.post("")
async def twilio_whatsapp_webhook(
    request: Request,
    background: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[AgentSessionStore, Depends(get_session_store)],
) -> dict[str, str]:
    """
    Inbound WhatsApp message from Twilio (sandbox or prod).
    Configure this URL (POST) under Twilio Sandbox or your WhatsApp sender's webhook.
    """
    form = await request.form()
    flat = await flat_form_to_str_dict(form)

    if settings.mitra_twilio_validate_webhook:
        token = settings.twilio_auth_token.strip()
        if not token:
            raise HTTPException(
                status_code=500,
                detail="MITRA_TWILIO_VALIDATE_WEBHOOK requires TWILIO_AUTH_TOKEN",
            )
        sig = request.headers.get("x-twilio-signature")
        full_url = _signature_url(request, settings)
        if not verify_twilio_request(
            full_url=full_url,
            post_params=flat,
            signature_header=sig,
            auth_token=token,
        ):
            log.warning("Twilio signature failed for url=%s", full_url)
            raise HTTPException(status_code=403, detail="invalid Twilio signature")

    from_raw = flat.get("From", "").strip()
    body_text = flat.get("Body", "").strip()

    # Extract media attachment (first item only)
    media_url: str | None = None
    media_type: str | None = None
    try:
        num_media = int(flat.get("NumMedia", "0"))
    except ValueError:
        num_media = 0

    if num_media > 0:
        media_url  = flat.get("MediaUrl0", "").strip() or None
        media_type = flat.get("MediaContentType0", "").strip() or None

    # Ignore only if there is no text AND no media
    if not body_text and not media_url:
        return {"status": "ignored_empty"}

    # If the candidate sent only a PDF (no caption), inject a synthetic body
    if not body_text and media_url:
        body_text = "I'm sharing my CV / resume."

    if not from_raw.lower().startswith("whatsapp:"):
        log.warning("Twilio webhook From is not WhatsApp: %s", from_raw[:40])
        raise HTTPException(status_code=400, detail="expected WhatsApp From prefix")

    session_id = normalize_twilio_session_id(from_raw)

    async def send_reply(msg: str) -> None:
        await send_whatsapp_reply(
            to_whatsapp_from_value=from_raw,
            body=msg,
            settings=settings,
        )

    # Account-linking flow: candidate sends "LINK XXXXXX" from WhatsApp
    upper_body = body_text.upper().strip()
    if upper_body.startswith("LINK "):
        token = upper_body[5:].strip()
        if token:
            email = await store.consume_wa_link_token(token)
            if email:
                web_sid = f"web:{email}"
                await store.merge_signals(session_id, {"_linked_web_sid": web_sid})
                log.info("WA link established: %s -> %s", session_id, web_sid)
                await send_reply(
                    "✅ Linked! Your WhatsApp is now connected to your Mitra account. "
                    "I'll pick up right where you left off."
                )
            else:
                await send_reply(
                    "This link code has expired or was already used. "
                    "Please generate a new one from your Mitra dashboard."
                )
            return {"status": "linked"}

    # Proactive match one-tap confirm: "yes" / "send it" / "yes send it"
    if _YES_PATTERN.match(body_text.strip()):
        signals_now = await store.get_signals(session_id)
        pending_job_id = signals_now.get("_pending_proactive_job_id")
        if pending_job_id:
            async def _auto_intro() -> None:
                try:
                    from mitra_api.db.engine import get_session_factory
                    from mitra_api.tools.intros import request_intro
                    factory = get_session_factory()
                    async with factory() as db:
                        result = await request_intro(
                            candidate_phone=session_id,
                            job_external_id=str(pending_job_id),
                            why_note="Candidate confirmed interest via proactive match notification.",
                            session=db,
                        )
                    # Clear the pending signal
                    await store.merge_signals(session_id, {
                        "_pending_proactive_job_id": None,
                        "_pending_proactive_score": None,
                    })
                    msg = result.get("message") or "Your intro has been sent!"
                    await send_reply(msg)
                except Exception:
                    log.exception("auto-intro failed for %s pending_job=%s", session_id, pending_job_id)
                    await send_reply(
                        "I hit a snag sending your intro — just reply and I'll sort it out manually."
                    )
            background.add_task(_auto_intro)
            return {"status": "ok"}

    background.add_task(
        run_agent_reply,
        sender_id=session_id,
        user_text=body_text,
        sessions=store,
        send_plain_text=send_reply,
        settings=settings,
        graph_recipient_digits=None,
        twilio_destination=from_raw.strip(),
        media_url=media_url,
        media_type=media_type,
    )
    return {"status": "ok"}
