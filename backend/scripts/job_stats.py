"""Quick stats on synced ATS jobs."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from mitra_api.db.engine import get_session_factory
from mitra_api.db.models import Company, Job, JobStatus


async def main() -> None:
    factory = get_session_factory()
    async with factory() as db:
        total = (
            await db.execute(
                select(func.count()).select_from(Job).where(Job.status == JobStatus.active)
            )
        ).scalar()
        print(f"Active jobs total: {total}")

        rows = (
            await db.execute(
                select(Job.company, func.count())
                .where(Job.status == JobStatus.active)
                .where(Job.external_id.isnot(None))
                .group_by(Job.company)
                .order_by(func.count().desc())
            )
        ).all()
        print("\nBy company (ATS-sourced):")
        for company, count in rows:
            print(f"  {company}: {count}")

        ats_companies = (
            await db.execute(
                select(Company.name, Company.greenhouse_slug, Company.lever_slug, Company.ashby_identifier)
                .where(
                    (Company.greenhouse_slug.isnot(None))
                    | (Company.lever_slug.isnot(None))
                    | (Company.ashby_identifier.isnot(None))
                )
                .order_by(Company.name)
            )
        ).all()
        print(f"\nCompanies with ATS ({len(ats_companies)}):")
        for name, gh, lv, ab in ats_companies:
            ats = f"gh={gh}" if gh else f"lever={lv}" if lv else f"ashby={ab}"
            print(f"  {name}: {ats}")


if __name__ == "__main__":
    asyncio.run(main())
