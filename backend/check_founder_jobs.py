"""
Check what founder briefs have been persisted to the jobs table.

Usage:
    cd backend
    python check_founder_jobs.py
"""

import asyncio
from dotenv import load_dotenv
load_dotenv()

from mitra_api.db.engine import get_session_factory
from mitra_api.db.models import Job, JobEmbedding
from sqlalchemy import select, func


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Job, func.count(JobEmbedding.id).label("has_emb"))
            .outerjoin(JobEmbedding, JobEmbedding.job_id == Job.id)
            .where(Job.external_id.like("founder:%"))
            .group_by(Job.id)
            .order_by(Job.created_at.desc())
        )
        rows = result.all()

    if not rows:
        print("No founder-submitted jobs found in the database yet.")
        print("Complete a founder onboarding conversation to trigger auto-submit.")
        return

    print(f"Found {len(rows)} founder-submitted job(s):\n")
    for job, has_emb in rows:
        print(f"  id={job.id}  status={job.status}")
        print(f"  title:    {job.title}")
        print(f"  company:  {job.company}")
        print(f"  stage:    {job.stage}")
        print(f"  location: {job.location}  remote_policy: {job.remote_policy}")
        print(f"  salary:   {job.salary_min_lpa}–{job.salary_max_lpa} LPA")
        print(f"  summary:  {(job.summary or '')[:120]}")
        print(f"  founder_wa:    {job.founder_wa}")
        print(f"  founder_email: {job.founder_email}")
        print(f"  embedding: {'✓' if has_emb else '✗ MISSING — run admin seed to regenerate'}")
        print(f"  external_id: {job.external_id}")
        print()


asyncio.run(main())
