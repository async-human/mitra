"""
mitra_api/scheduler.py

Scheduled task runner — executes all proactive workflows on a cron schedule.

Wired into main.py lifespan:

    from mitra_api.scheduler import start_scheduler, stop_scheduler

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        scheduler_tasks = await start_scheduler()
        yield
        await stop_scheduler(scheduler_tasks)

Or run standalone for one-off testing:
    python -m mitra_api.scheduler [reengagement|followup|checkin30|checkin90]

Schedule:
  Every 2 hours  — candidate re-engagement check
  Every 4 hours  — intro follow-up nudge to unresponsive founders
  Daily at 09:00 — 30-day post-placement check-in
  Daily at 09:30 — 90-day post-placement check-in
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

_TASKS: list[asyncio.Task] = []


# ── INDIVIDUAL JOBS ───────────────────────────────────────────────────────────

async def run_candidate_reengagement() -> None:
    """Re-engage candidates who went quiet mid-intake."""
    log.info("scheduler: candidate_reengagement starting")
    try:
        from mitra_api.db.engine import get_session_factory
        from mitra_api.tools.proactive import (
            get_stale_candidates,
            build_re_engagement_message,
            send_proactive_message,
        )
        factory = get_session_factory()
        async with factory() as db:
            stale = await get_stale_candidates(db, idle_hours=48)
            log.info("scheduler: found %d stale candidates", len(stale))
            sent = 0
            for candidate in stale[:20]:
                msg = build_re_engagement_message(candidate)
                ok  = await send_proactive_message(
                    candidate["phone"], msg, label="re-engagement"
                )
                if ok:
                    sent += 1
            log.info("scheduler: candidate_reengagement sent=%d", sent)
    except Exception:
        log.exception("scheduler: candidate_reengagement failed")


async def run_intro_followup() -> None:
    """Nudge founders who haven't replied to intros in 48h."""
    log.info("scheduler: intro_followup starting")
    try:
        from mitra_api.db.engine import get_session_factory
        from mitra_api.tools.proactive import (
            get_intros_needing_followup,
            build_founder_followup_message,
            send_proactive_message,
        )
        from mitra_api.tools.email import send_email

        factory = get_session_factory()
        async with factory() as db:
            intros = await get_intros_needing_followup(db, hours_since_sent=48)
            log.info("scheduler: found %d intros needing followup", len(intros))
            for intro in intros[:10]:
                msg = build_founder_followup_message(intro)
                if intro.get("founder_wa"):
                    await send_proactive_message(
                        intro["founder_wa"], msg, label="intro-followup"
                    )
                elif intro.get("founder_email"):
                    await send_email(
                        to=intro["founder_email"],
                        subject=(
                            f"Following up: {intro['candidate_name']} — "
                            f"{intro['job_title']}"
                        ),
                        text=msg,
                    )
    except Exception:
        log.exception("scheduler: intro_followup failed")


async def run_placement_checkins(days: int = 30) -> None:
    """Check in with both sides at 30-day and 90-day post-placement."""
    log.info("scheduler: placement_checkins(%dd) starting", days)
    try:
        from mitra_api.db.engine import get_session_factory
        from mitra_api.tools.proactive import (
            get_placements_for_checkin,
            build_candidate_checkin_message,
            build_founder_checkin_message,
            send_proactive_message,
        )
        from mitra_api.tools.email import send_email

        factory = get_session_factory()
        async with factory() as db:
            placements = await get_placements_for_checkin(db, days=days)
            log.info(
                "scheduler: found %d placements for %dd checkin",
                len(placements), days,
            )
            for p in placements:
                # Message candidate (WhatsApp only — web candidates skipped)
                phone = p.get("candidate_phone", "")
                if phone and not phone.startswith("web:"):
                    msg = build_candidate_checkin_message(p)
                    await send_proactive_message(
                        phone, msg, label=f"checkin-{days}d-candidate"
                    )

                # Message founder
                if p.get("founder_wa") or p.get("founder_email"):
                    msg = build_founder_checkin_message(p)
                    if p.get("founder_wa"):
                        await send_proactive_message(
                            p["founder_wa"], msg, label=f"checkin-{days}d-founder"
                        )
                    elif p.get("founder_email"):
                        await send_email(
                            to=p["founder_email"],
                            subject=(
                                f"Quick check-in: {p.get('candidate_name')} "
                                f"at {p.get('company')}"
                            ),
                            text=msg,
                        )
    except Exception:
        log.exception("scheduler: placement_checkins(%dd) failed", days)


# ── LOOP WRAPPERS ─────────────────────────────────────────────────────────────

async def _every(seconds: int, coro_fn, *args, **kwargs) -> None:
    """Run coro_fn every `seconds` seconds indefinitely."""
    while True:
        try:
            await coro_fn(*args, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("scheduler loop error in %s", coro_fn.__name__)
        await asyncio.sleep(seconds)


async def _daily_at(hour: int, minute: int, coro_fn, *args, **kwargs) -> None:
    """Run coro_fn once per day at the specified UTC hour:minute."""
    while True:
        now    = datetime.now(timezone.utc)
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target = target + timedelta(days=1)  # safe: timedelta handles month rollover
        wait = (target - now).total_seconds()
        await asyncio.sleep(wait)
        try:
            await coro_fn(*args, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("scheduler daily error in %s", coro_fn.__name__)


# ── START / STOP ──────────────────────────────────────────────────────────────

async def start_scheduler() -> list[asyncio.Task]:
    """
    Start all background scheduler tasks.
    Called from FastAPI lifespan on startup.
    Returns list of tasks (pass to stop_scheduler on shutdown).
    """
    from mitra_api.config import get_settings
    s = get_settings()

    if not s.mitra_database_url:
        log.info("scheduler: MITRA_DATABASE_URL not set — scheduler disabled")
        return []

    tasks = [
        asyncio.create_task(
            _every(2 * 3600, run_candidate_reengagement),
            name="re-engagement",
        ),
        asyncio.create_task(
            _every(4 * 3600, run_intro_followup),
            name="intro-followup",
        ),
        asyncio.create_task(
            _daily_at(9, 0, run_placement_checkins, 30),
            name="checkin-30d",
        ),
        asyncio.create_task(
            _daily_at(9, 30, run_placement_checkins, 90),
            name="checkin-90d",
        ),
    ]

    global _TASKS
    _TASKS = tasks
    log.info("scheduler: started %d tasks", len(tasks))
    return tasks


async def stop_scheduler(tasks: list[asyncio.Task] | None = None) -> None:
    """Cancel all scheduler tasks gracefully."""
    to_cancel = tasks or _TASKS
    for task in to_cancel:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    log.info("scheduler: all tasks stopped")


# ── STANDALONE RUNNER ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    async def main():
        cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
        if cmd == "reengagement":
            await run_candidate_reengagement()
        elif cmd == "followup":
            await run_intro_followup()
        elif cmd == "checkin30":
            await run_placement_checkins(30)
        elif cmd == "checkin90":
            await run_placement_checkins(90)
        else:
            log.info("Running all jobs once...")
            await run_candidate_reengagement()
            await run_intro_followup()
            await run_placement_checkins(30)
            await run_placement_checkins(90)

    asyncio.run(main())
