"""
Quick test for warm intro sending.

Usage:
    cd backend
    python test_intro.py --candidate +91XXXXXXXXXX --job <external_id> --to +91XXXXXXXXXX

--candidate  WhatsApp number of the candidate already in your DB
--job        external_id of the job (check jobs table, or use "founder:<session_id>")
--to         Override founder_wa on that job to your own number for testing
             (skipped if not provided — uses whatever is already on the job)
"""

import argparse
import asyncio
import sys

from dotenv import load_dotenv
load_dotenv()

from mitra_api.db.engine import get_session_factory
from mitra_api.db.models import Job
from mitra_api.tools.intros import request_intro
from sqlalchemy import select


async def main(candidate_phone: str, job_external_id: str, override_wa: str | None) -> None:
    factory = get_session_factory()

    async with factory() as session:
        # Optionally point founder_wa at your own number for testing
        if override_wa:
            job = (await session.execute(
                select(Job).where(Job.external_id == job_external_id)
            )).scalar_one_or_none()

            if not job:
                print(f"ERROR: job '{job_external_id}' not found")
                sys.exit(1)

            print(f"Overriding founder_wa on job '{job_external_id}' → {override_wa}")
            job.founder_wa = override_wa
            await session.commit()

        # Fire the intro
        result = await request_intro(
            candidate_phone=candidate_phone,
            job_external_id=job_external_id,
            why_note=(
                "Strong backend engineer with 5+ years in Python and FastAPI. "
                "Has built systems at scale and is actively looking for a founding-team role."
            ),
            session=session,
        )

    print("\n── Result ──────────────────────────────────────────")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, help="Candidate WhatsApp number, e.g. +917012345678")
    parser.add_argument("--job",       required=True, help="Job external_id")
    parser.add_argument("--to",        default=None,  help="Override founder_wa with this number for testing")
    args = parser.parse_args()

    asyncio.run(main(args.candidate, args.job, args.to))
