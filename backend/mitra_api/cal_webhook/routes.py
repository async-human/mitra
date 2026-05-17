"""
mitra_api/cal_webhook/routes.py

POST /webhook/cal-booking

Receives Cal.com booking events and closes the scheduling loop:

  BOOKING_CREATED     → update intro to interview, confirm both sides via email
  BOOKING_CANCELLED   → revert intro to acknowledged, notify both sides
  BOOKING_RESCHEDULED → update interview_details with new time, notify both sides

Cal.com sends a HMAC-SHA256 signature in X-Cal-Signature-256 so we can
verify the request is genuine. Set CAL_WEBHOOK_SECRET to the secret you
configured in Cal.com → Settings → Webhooks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook/cal-booking")
async def cal_booking_webhook(
    request: Request,
    x_cal_signature_256: str = Header(default=""),
) -> JSONResponse:
    from mitra_api.config import get_settings
    from mitra_api.tools.cal import extract_booking_info, verify_cal_signature

    s    = get_settings()
    body = await request.body()

    if not verify_cal_signature(body, x_cal_signature_256, s.cal_webhook_secret):
        raise HTTPException(403, "Invalid Cal.com webhook signature")

    try:
        import json
        data = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    event   = data.get("triggerEvent", "")
    payload = data.get("payload", {})

    log.info("cal-webhook: event=%s uid=%s", event, payload.get("uid"))

    if event == "BOOKING_CREATED":
        await _handle_booking_created(payload)
    elif event == "BOOKING_CANCELLED":
        await _handle_booking_cancelled(payload)
    elif event == "BOOKING_RESCHEDULED":
        await _handle_booking_rescheduled(payload)
    else:
        log.debug("cal-webhook: unhandled event=%s", event)

    return JSONResponse({"status": "ok", "event": event})


# ── BOOKING CREATED ───────────────────────────────────────────────────────────

async def _handle_booking_created(payload: dict[str, Any]) -> None:
    from mitra_api.tools.cal import extract_booking_info
    info = extract_booking_info(payload)

    log.info(
        "cal-booking created: intro_id=%s candidate=%s time=%s meeting=%s",
        info["intro_id"], info["candidate_email"],
        info["start_time_fmt"], info["meeting_url"] or "(no link)",
    )

    intro_id = info["intro_id"]
    if not intro_id:
        log.warning("cal-booking: no intro_id in metadata — cannot link to intro")
        return

    # ── Update intro in DB ────────────────────────────────────────────────────
    founder_email = await _update_intro_to_interview(info)

    # ── Send confirmation emails ──────────────────────────────────────────────
    await _send_candidate_confirmation(info)
    await _send_founder_confirmation(info, founder_email)


async def _update_intro_to_interview(info: dict[str, Any]) -> str | None:
    """Update intro status to interview, store details. Returns founder email."""
    from mitra_api.db.engine import get_session_factory
    from mitra_api.db.models import Candidate, Intro, IntroStatus, Job
    from sqlalchemy import select

    intro_id = info["intro_id"]
    now = datetime.now(timezone.utc)

    try:
        factory = get_session_factory()
        async with factory() as db:
            row = (await db.execute(
                select(Intro, Job)
                .join(Job, Intro.job_id == Job.id)
                .where(Intro.id == intro_id)
            )).first()

            if not row:
                log.warning("cal-booking: intro_id=%d not found in DB", intro_id)
                return None

            intro, job = row
            intro.status     = IntroStatus.interview
            intro.updated_at = now

            # Only set interview_at if not already set (don't overwrite if rescheduled)
            if not intro.interview_at:
                intro.interview_at = now

            intro.interview_details = {
                "scheduled_at": info["start_time_fmt"],
                "scheduled_at_iso": info["start_time_iso"],
                "format":       info["meeting_app"],
                "link":         info["meeting_url"],
                "booking_uid":  info["booking_uid"],
                "notes":        "Booked via Cal.com",
            }
            await db.commit()

            log.info(
                "intro %d → interview scheduled at %s via %s",
                intro_id, info["start_time_fmt"], info["meeting_app"],
            )
            return job.founder_email
    except Exception:
        log.exception("cal-booking: DB update failed for intro_id=%d", intro_id)
        return None


async def _send_candidate_confirmation(info: dict[str, Any]) -> None:
    from mitra_api.tools.email import send_email

    cand_email  = info.get("candidate_email")
    cand_first  = (info.get("candidate_name") or "there").split()[0]
    company     = info.get("company", "the company")
    role        = info.get("role", "the role")
    time_fmt    = info.get("start_time_fmt", "TBD")
    meeting_url = info.get("meeting_url", "")
    meeting_app = info.get("meeting_app", "video call")
    intro_id    = info.get("intro_id")

    if not cand_email:
        return

    meeting_line = (
        f"\n{meeting_app} link: {meeting_url}\n"
        if meeting_url else
        "\nThe founder will send you a meeting link shortly.\n"
    )

    await send_email(
        to=cand_email,
        subject=f"Interview confirmed: {company} — {time_fmt}",
        text=(
            f"Hey {cand_first}!\n\n"
            f"Your interview with {company} for the {role} role is confirmed.\n\n"
            f"When: {time_fmt}"
            f"{meeting_line}\n"
            f"You'll also receive a calendar invite directly from Cal.com.\n\n"
            f"Good luck — I'm rooting for you. Let me know how it goes!\n\n"
            f"— Mitra"
        ),
        reply_context={"type": "candidate", "intro_id": intro_id} if intro_id else None,
    )
    log.info("cal-booking: confirmation sent to candidate %s", cand_email)


async def _send_founder_confirmation(
    info: dict[str, Any],
    founder_email: str | None,
) -> None:
    from mitra_api.tools.email import send_email

    if not founder_email:
        return

    cand_name   = info.get("candidate_name", "the candidate")
    role        = info.get("role", "the role")
    time_fmt    = info.get("start_time_fmt", "TBD")
    meeting_url = info.get("meeting_url", "")
    meeting_app = info.get("meeting_app", "video call")
    intro_id    = info.get("intro_id")

    meeting_line = (
        f"\n{meeting_app} link: {meeting_url}\n"
        if meeting_url else
        "\nA meeting link has been generated — check your calendar invite.\n"
    )

    await send_email(
        to=founder_email,
        subject=f"Interview booked: {cand_name} — {time_fmt}",
        text=(
            f"Your intro call with {cand_name} for {role} is confirmed.\n\n"
            f"When: {time_fmt}"
            f"{meeting_line}\n"
            f"You'll receive a calendar invite from Cal.com. "
            f"I'll follow up after the interview to see how it went.\n\n"
            f"— Mitra"
        ),
        reply_context={"type": "founder", "intro_id": intro_id} if intro_id else None,
    )
    log.info("cal-booking: confirmation sent to founder %s", founder_email)


# ── BOOKING CANCELLED ─────────────────────────────────────────────────────────

async def _handle_booking_cancelled(payload: dict[str, Any]) -> None:
    from mitra_api.tools.cal import extract_booking_info
    from mitra_api.tools.email import send_email

    info     = extract_booking_info(payload)
    intro_id = info["intro_id"]

    # Revert intro to acknowledged so the scheduler nudge can fire again
    if intro_id:
        try:
            from mitra_api.db.engine import get_session_factory
            from mitra_api.db.models import Intro, IntroStatus, Job
            from sqlalchemy import select

            now = datetime.now(timezone.utc)
            factory = get_session_factory()
            async with factory() as db:
                row = (await db.execute(
                    select(Intro, Job)
                    .join(Job, Intro.job_id == Job.id)
                    .where(Intro.id == intro_id)
                )).first()
                if row:
                    intro, job = row
                    intro.status       = IntroStatus.acknowledged
                    intro.interview_at = None
                    intro.updated_at   = now
                    await db.commit()

                    # Notify both sides
                    cand_first  = (info.get("candidate_name") or "there").split()[0]
                    cand_email  = info.get("candidate_email")
                    found_email = job.founder_email

                    if cand_email:
                        await send_email(
                            to=cand_email,
                            subject=f"Interview cancelled: {info.get('company')}",
                            text=(
                                f"Hey {cand_first},\n\n"
                                f"The interview slot has been cancelled. "
                                f"I'll reach out to reschedule — no action needed on your end.\n\n"
                                f"— Mitra"
                            ),
                        )
                    if found_email:
                        await send_email(
                            to=found_email,
                            subject=f"Interview cancelled: {info.get('candidate_name')}",
                            text=(
                                f"The interview with {info.get('candidate_name')} was cancelled. "
                                f"I'll follow up to find a new time that works.\n\n— Mitra"
                            ),
                        )
                    log.info("cal-booking cancelled: intro=%d reverted to acknowledged", intro_id)
        except Exception:
            log.exception("cal-booking: cancellation handling failed for intro_id=%s", intro_id)


# ── BOOKING RESCHEDULED ───────────────────────────────────────────────────────

async def _handle_booking_rescheduled(payload: dict[str, Any]) -> None:
    from mitra_api.tools.cal import extract_booking_info

    info     = extract_booking_info(payload)
    intro_id = info["intro_id"]

    if not intro_id:
        return

    try:
        from mitra_api.db.engine import get_session_factory
        from mitra_api.db.models import Intro, Job
        from sqlalchemy import select

        now = datetime.now(timezone.utc)
        factory = get_session_factory()
        async with factory() as db:
            row = (await db.execute(
                select(Intro, Job)
                .join(Job, Intro.job_id == Job.id)
                .where(Intro.id == intro_id)
            )).first()
            if row:
                intro, job = row
                intro.interview_at = now
                intro.updated_at   = now
                intro.interview_details = {
                    **(intro.interview_details or {}),
                    "scheduled_at":     info["start_time_fmt"],
                    "scheduled_at_iso": info["start_time_iso"],
                    "link":             info["meeting_url"] or (intro.interview_details or {}).get("link"),
                    "notes":            "Rescheduled via Cal.com",
                }
                await db.commit()

        # Re-send confirmations with updated time
        founder_email = row[1].founder_email if row else None
        await _send_candidate_confirmation(info)
        await _send_founder_confirmation(info, founder_email)
        log.info("cal-booking rescheduled: intro=%d new time=%s", intro_id, info["start_time_fmt"])

    except Exception:
        log.exception("cal-booking: reschedule handling failed for intro_id=%s", intro_id)
