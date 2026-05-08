"""Shared agent turn + outbound send (used by Meta Cloud and Twilio webhooks)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from mitra_api.agent.orchestrator import run_agent_turn
from mitra_api.agent.session_store import AgentSessionStore
from mitra_api.config import Settings, get_settings
from mitra_api.twilio_whatsapp.list_picker import send_twilio_native_job_list_message
from mitra_api.whatsapp.meta_interactive import send_interactive_job_list_message
from mitra_api.whatsapp.split_text import split_whatsapp_text

log = logging.getLogger(__name__)

SendPlainText = Callable[[str], Awaitable[None]]


async def run_agent_reply(
    *,
    sender_id: str,
    user_text: str,
    sessions: AgentSessionStore,
    send_plain_text: SendPlainText,
    settings: Settings | None = None,
    graph_recipient_digits: str | None = None,
    twilio_destination: str | None = None,
    media_url: str | None = None,
    media_type: str | None = None,
) -> None:
    """
    Sends job recommendations as WhatsApp-native *interactive lists* when possible
    (session messages). Falls back to the plaintext recommendation chain otherwise.
    """

    async def send_parts(parts: tuple[str, ...]) -> None:
        for part in parts:
            for segment in split_whatsapp_text(part):
                if not segment.strip():
                    continue
                try:
                    await send_plain_text(segment.strip())
                except Exception:
                    log.warning(
                        "send_parts: failed to deliver segment to %s (%.60s…) — continuing",
                        sender_id, segment,
                    )

    s = settings or get_settings()
    try:
        turn = await run_agent_turn(
            whatsapp_sender_id=sender_id,
            user_text=user_text,
            sessions=sessions,
            settings=s,
            media_url=media_url,
            media_type=media_type,
        )

        can_meta = bool(
            graph_recipient_digits and s.whatsapp_phone_number_id.strip() and s.whatsapp_access_token.strip()
        )
        can_twilio = bool(
            twilio_destination
            and s.twilio_account_sid.strip()
            and s.twilio_auth_token.strip()
            and s.twilio_whatsapp_from.strip()
        )

        if turn.native_list_rows and s.mitra_whatsapp_native_list:
            if turn.whatsapp_intro:
                for seg in split_whatsapp_text(turn.whatsapp_intro):
                    if seg.strip():
                        await send_plain_text(seg.strip())

            list_body = (
                "Tap *View picks* below — each row is one Mitra-shortlisted opening (company, "
                "fit %, stacks / location)."
            )[:1024]

            native_sent = False

            if can_meta:
                try:
                    footer_meta = (
                        turn.whatsapp_outro[0].strip()[:60] if turn.whatsapp_outro else None
                    ) or None
                    await send_interactive_job_list_message(
                        to_digits=graph_recipient_digits.strip(),
                        body_text=list_body,
                        footer_text=footer_meta,
                        button_label="View picks",
                        rows=turn.native_list_rows,
                        settings=s,
                    )
                    native_sent = True
                    await send_parts(tuple(turn.whatsapp_outro[1:]))
                except Exception:
                    log.exception("Meta native list failed; trying Twilio or plaintext")

            if not native_sent and can_twilio:
                try:
                    native_sent = await send_twilio_native_job_list_message(
                        account_sid=s.twilio_account_sid,
                        auth_token=s.twilio_auth_token,
                        from_whatsapp=s.twilio_whatsapp_from,
                        to_whatsapp=twilio_destination.strip(),
                        body=list_body,
                        button_label="View picks",
                        rows=turn.native_list_rows,
                    )
                    if native_sent:
                        await send_parts(turn.whatsapp_outro)
                except Exception:
                    log.exception("Twilio native list failed; using plaintext")

            if native_sent:
                return

        await send_parts(turn.whatsapp_fallback_plain_parts)
    except Exception:
        log.exception("agent failed for sender %s", sender_id)
        try:
            await send_plain_text(
                "Sorry—something went wrong on our side. Please try again in a moment.",
            )
        except Exception as delivery_err:
            log.warning("could not deliver error reply to %s: %s", sender_id, delivery_err)
