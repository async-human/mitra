"""
mitra_api/tools/company_enrichment_scheduler.py

Keeps funded_startups data fresh automatically.

Three refresh cycles:

  DAILY    — RSS pipeline runs at 00:30, upserts new rounds with merge logic
  WEEKLY   — Sunday 02:00: re-verify websites, backfill missing websites,
              flag stale records; processes 50 rows per run to avoid timeouts
  EVENT    — funding_tracker upsert already handles stage upgrades via
              _upsert_funded_startup merge rules (stage only moves forward)

Merge rules (never lose data):
  - Stage only moves forward: Series A → Series B OK, reverse never happens
  - amount_usd updates to the higher value (later rounds are larger)
  - investors: union of both lists
  - Null never overwrites a known value
  - Website re-verified on each weekly cycle
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

log = logging.getLogger(__name__)

ENRICHMENT_STALE_DAYS = 7
WEBSITE_STALE_DAYS    = 30

_STAGE_ORDER = {
    "pre-seed": 1, "pre_seed": 1,
    "seed":     2,
    "series a": 3, "series_a": 3,
    "series b": 4, "series_b": 4,
    "series c": 5, "series_c": 5,
    "series d": 6, "series_d": 6,
    "series e": 7, "series_e": 7,
    "series f": 8, "series_f": 8,
    "growth":   9,
    "ipo":     10,
}


def _stage_rank(stage: str | None) -> int:
    if not stage:
        return 0
    return _STAGE_ORDER.get(stage.lower().strip(), 0)


def merge_funded_startup(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """
    Merge incoming funding event data into existing record.
    Returns (merged, changed_fields).

    Rules:
    - Stage only moves forward (never backwards)
    - amount_usd takes the higher value
    - investors: union of both lists
    - All other fields: incoming wins only when non-null and different
    """
    merged  = dict(existing)
    changed: list[str] = []

    # Stage — only upgrade
    new_stage = incoming.get("stage")
    old_stage = existing.get("stage")
    if new_stage and _stage_rank(new_stage) > _stage_rank(old_stage):
        merged["stage"] = new_stage
        changed.append("stage")
        log.info("company_merge: stage upgrade %s → %s", old_stage, new_stage)

    # Amount — take the higher value
    new_amount = incoming.get("amount_usd") or 0
    old_amount = existing.get("amount_usd") or 0
    if new_amount and new_amount > old_amount:
        merged["amount_usd"] = new_amount
        changed.append("amount_usd")

    # Investors — union
    new_inv = incoming.get("investors") or []
    old_inv = existing.get("investors") or []
    if isinstance(new_inv, list) and new_inv:
        merged_inv = list({*old_inv, *new_inv})
        if set(merged_inv) != set(old_inv):
            merged["investors"] = merged_inv
            changed.append("investors")

    # Founder name — fill in if missing
    if incoming.get("founder_name") and not existing.get("founder_name"):
        merged["founder_name"] = incoming["founder_name"]
        changed.append("founder_name")

    # funded_at — take the newer timestamp
    new_funded = incoming.get("funded_at")
    old_funded = existing.get("funded_at")
    if new_funded and (not old_funded or str(new_funded) > str(old_funded)):
        merged["funded_at"] = new_funded
        changed.append("funded_at")

    return merged, changed


# ── Weekly enrichment ─────────────────────────────────────────────────────────

async def run_weekly_funded_startup_enrichment(db) -> dict[str, int]:
    """
    Weekly refresh for funded_startups rows:
      1. Re-verify website URLs — remove dead links, find better ones
      2. Backfill missing websites using the 4-layer resolver
      3. Mark enriched_at so the row isn't processed again for 7 days

    Processes up to 50 rows per run (avoids timeouts).
    Prioritises rows with enriched_at = NULL (never enriched).
    """
    from mitra_api.db.models import FundedStartup
    from mitra_api.tools.website_resolver import resolve_company_website
    from sqlalchemy import select, or_

    cutoff = datetime.now(timezone.utc) - timedelta(days=ENRICHMENT_STALE_DAYS)

    rows = (await db.execute(
        select(FundedStartup)
        .where(
            or_(
                FundedStartup.enriched_at.is_(None),
                FundedStartup.enriched_at < cutoff,
            )
        )
        .order_by(FundedStartup.enriched_at.asc().nullsfirst())
        .limit(50)
    )).scalars().all()

    log.info("weekly_enrichment: %d funded_startups to process", len(rows))

    stats = {
        "processed":       0,
        "website_found":   0,
        "website_updated": 0,
        "website_dead":    0,
        "no_change":       0,
        "errors":          0,
    }

    for row in rows:
        try:
            changed = False

            if row.website:
                # Re-verify existing URL
                from mitra_api.tools.website_resolver import _verify_url
                still_live = await _verify_url(row.website)
                if not still_live:
                    log.info("weekly_enrichment: dead website for %s: %s", row.name, row.website)
                    row.website = None
                    stats["website_dead"] += 1
                    changed = True

            if not row.website:
                # Resolve fresh
                url = await resolve_company_website(row.name, sector=row.sector)
                if url:
                    row.website = url
                    stats["website_found"] += 1
                    changed = True

            row.enriched_at = datetime.now(timezone.utc)
            stats["processed"] += 1

            if changed:
                stats["website_updated"] += 1
            else:
                stats["no_change"] += 1

        except Exception:
            log.exception("weekly_enrichment: failed for %s", row.name)
            stats["errors"] += 1

    await db.commit()
    log.info("weekly_enrichment done: %s", stats)
    return stats
