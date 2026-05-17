"""
mitra_api/tools/cal.py

Cal.com scheduling integration — zero back-and-forth, fully automated.

Flow:
  1. Intro moves to acknowledged (founder portal or email reply)
  2. Scheduler nudge fires → build_booking_link() → candidate gets a self-
     service link showing the founder's real availability
  3. Candidate picks a slot → Cal.com handles the calendar invite + meeting link
  4. Cal.com POSTs to /webhook/cal-booking → we update the intro + send
     personalised confirmation emails to both sides

Setup (one-time):
  1. Create a Cal.com account at cal.com
  2. Create an event type "30-min Intro Call" — note the URL slug
  3. Go to Integrations → connect Google Meet or Zoom (auto-creates meeting
     links on every booking)
  4. Go to Settings → Webhooks → add a webhook:
       URL:    https://YOUR_RAILWAY_URL/webhook/cal-booking
       Events: BOOKING_CREATED, BOOKING_CANCELLED, BOOKING_RESCHEDULED
       Secret: any random string (copy to CAL_WEBHOOK_SECRET env var)
  5. Set env vars in Railway:
       CAL_BOOKING_URL    = https://cal.com/<username>/<event-slug>
       CAL_WEBHOOK_SECRET = <the secret you set above>
"""

from __future__ import annotations

import hashlib
import hmac
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any


# ── BOOKING LINK BUILDER ──────────────────────────────────────────────────────

def build_booking_link(
    booking_base_url: str,
    *,
    intro_id: int,
    candidate_name: str,
    candidate_email: str,
    company: str,
    role: str,
) -> str:
    """
    Build a personalised Cal.com booking link for one candidate-intro pair.

    Cal.com pre-fills name/email in the booking form and passes the metadata
    dict back verbatim in the BOOKING_CREATED webhook — that's how we know
    which intro to update when the candidate picks a slot.
    """
    if not booking_base_url:
        return ""

    params: dict[str, str] = {
        "name":              candidate_name,
        "email":             candidate_email,
        "metadata[intro_id]": str(intro_id),
        "metadata[company]": company,
        "metadata[role]":    role,
    }
    return f"{booking_base_url.rstrip('/')}?{urllib.parse.urlencode(params)}"


# ── WEBHOOK VALIDATION ────────────────────────────────────────────────────────

def verify_cal_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Validate Cal.com HMAC-SHA256 webhook signature.
    Cal.com sends: X-Cal-Signature-256: <hex digest of body>
    Returns True if no secret is configured (dev / test mode).
    """
    if not secret:
        return True
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── PAYLOAD PARSER ────────────────────────────────────────────────────────────

def extract_booking_info(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Normalise a Cal.com BOOKING_CREATED payload into the fields we use.
    The payload is the value of body["payload"] from the webhook POST.
    """
    metadata  = payload.get("metadata") or {}
    attendees = payload.get("attendees") or []
    vc        = payload.get("videoCallData") or {}
    organizer = payload.get("organizer") or {}

    candidate = attendees[0] if attendees else {}

    meeting_type_map = {
        "google_meet_video": "Google Meet",
        "zoom_video":        "Zoom",
        "teams_video":       "Microsoft Teams",
        "daily_video":       "Daily.co",
    }
    raw_type    = vc.get("type", "")
    meeting_app = meeting_type_map.get(raw_type, "Video call")

    return {
        "intro_id":        _int_or_none(metadata.get("intro_id")),
        "company":         metadata.get("company", ""),
        "role":            metadata.get("role", ""),
        "start_time_iso":  payload.get("startTime", ""),
        "end_time_iso":    payload.get("endTime", ""),
        "start_time_fmt":  _fmt_ist(payload.get("startTime", "")),
        "meeting_url":     vc.get("url", ""),
        "meeting_app":     meeting_app,
        "booking_uid":     payload.get("uid", ""),
        "candidate_name":  candidate.get("name", ""),
        "candidate_email": candidate.get("email", ""),
        "organizer_name":  organizer.get("name", "Mitra"),
        "organizer_email": organizer.get("email", ""),
    }


def _fmt_ist(iso_str: str) -> str:
    """Convert ISO UTC timestamp → human-readable IST string."""
    if not iso_str:
        return "TBD"
    try:
        dt_utc = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        ist     = timezone(timedelta(hours=5, minutes=30))
        dt_ist  = dt_utc.astimezone(ist)
        return dt_ist.strftime("%A, %d %B at %I:%M %p IST")
    except Exception:
        return iso_str


def _int_or_none(val: Any) -> int | None:
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None
