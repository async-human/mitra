#!/usr/bin/env python3
"""
Bootstrap Indian startup roles into Mitra's job catalog.

Usage (from backend/):
  python scripts/bootstrap_ats.py
  python scripts/bootstrap_ats.py --dry-run
  python scripts/bootstrap_ats.py --company Pronto --slug pronto
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Allow running as: python scripts/bootstrap_ats.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("bootstrap_ats")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap ATS companies and sync jobs")
    parser.add_argument("--dry-run", action="store_true", help="Discover only, no DB writes")
    parser.add_argument("--company", help="Sync one company by name")
    parser.add_argument("--slug", help="Greenhouse slug (with --company)")
    parser.add_argument("--discover", help="Run ATS discovery for one company name")
    args = parser.parse_args()

    from mitra_api.db.engine import get_session_factory, run_schema_migrations
    from mitra_api.tools.funding_tracker import bootstrap_known_startups, discover_ats
    from mitra_api.tools.funding_tracker import _upsert_company_with_ats, _sync_company_jobs

    await run_schema_migrations()

    if args.discover:
        result = await discover_ats(args.discover)
        print(result or {"ats": None})
        return

    if args.company and args.slug:
        factory = get_session_factory()
        async with factory() as db:
            ats_info = {
                "ats": "greenhouse",
                "slug": args.slug,
                "board_url": f"https://boards.greenhouse.io/{args.slug}",
            }
            company, created = await _upsert_company_with_ats(
                db,
                company_name=args.company,
                ats_info=ats_info,
                stage=None,
                sector=None,
                location="India",
                extra_signals={"manual_bootstrap": True},
            )
            await db.commit()
            synced = await _sync_company_jobs(company.id, "greenhouse")
            log.info(
                "Synced %s (id=%s created=%s) — %d new jobs",
                args.company, company.id, created, synced,
            )
        return

    factory = get_session_factory()
    async with factory() as db:
        stats = await bootstrap_known_startups(db, dry_run=args.dry_run)
    log.info("Bootstrap complete: %s", stats)


if __name__ == "__main__":
    asyncio.run(main())
