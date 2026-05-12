"""
mitra_api/db/engine.py

Async SQLAlchemy engine wired to MITRA_DATABASE_URL.
Imported by tools that need DB access. Never imported by the LLM layer directly.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mitra_api.config import get_settings


def _as_async_database_url(raw_url: str) -> str:
    """
    Normalize DB URL for SQLAlchemy asyncio engine.

    Accepts common Postgres sync URLs (postgresql://...) and upgrades them
    to asyncpg to avoid runtime InvalidRequestError.
    """
    parsed = make_url(raw_url)
    driver = parsed.drivername
    if driver in {"postgresql", "postgres"} or driver.startswith("postgresql+psycopg"):
        return str(parsed.set(drivername="postgresql+asyncpg"))
    return raw_url


@lru_cache(maxsize=1)
def _engine():
    url = get_settings().mitra_database_url
    if not url:
        raise RuntimeError("MITRA_DATABASE_URL is not set")
    # asyncpg driver: postgresql+asyncpg://user:pass@host/db
    normalized_url = _as_async_database_url(url)
    return create_async_engine(
        normalized_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(_engine(), expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields one session per request."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def run_schema_migrations() -> None:
    """
    Idempotent schema migrations — ADD COLUMN IF NOT EXISTS for columns added
    after initial table creation (no Alembic required).
    Also backfills any NULL tokens so existing rows work immediately.
    """
    import logging
    import secrets
    from sqlalchemy import text

    log = logging.getLogger(__name__)

    migrations = [
        # Intro.response_token — one-click founder reply token
        "ALTER TABLE intros ADD COLUMN IF NOT EXISTS response_token VARCHAR(64)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_intros_response_token ON intros(response_token) WHERE response_token IS NOT NULL",
        # Job.founder_access_token — persistent no-login founder portal token
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS founder_access_token VARCHAR(64)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_jobs_founder_access_token ON jobs(founder_access_token) WHERE founder_access_token IS NOT NULL",
        # Intro.decline_reason — founder's reason when passing on a candidate
        "ALTER TABLE intros ADD COLUMN IF NOT EXISTS decline_reason TEXT",
        # Intro.updated_at — last-modified timestamp
        "ALTER TABLE intros ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
        # matches table — dimensional fit scores + founder outcome tracking
        """CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            candidate_id INTEGER NOT NULL REFERENCES candidates(id),
            job_id INTEGER NOT NULL REFERENCES jobs(id),
            intro_id INTEGER REFERENCES intros(id),
            salary_fit FLOAT,
            location_fit FLOAT,
            skill_fit FLOAT,
            overall_fit FLOAT,
            reranker_rank INTEGER,
            reranker_fit_pct INTEGER,
            reranker_why TEXT,
            intro_sent BOOLEAN NOT NULL DEFAULT FALSE,
            gate_blocked BOOLEAN NOT NULL DEFAULT FALSE,
            gate_missing JSONB,
            founder_action VARCHAR(30),
            founder_feedback TEXT,
            matched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            decided_at TIMESTAMPTZ
        )""",
        "CREATE INDEX IF NOT EXISTS matches_candidate_idx ON matches(candidate_id)",
        "CREATE INDEX IF NOT EXISTS matches_job_idx ON matches(job_id)",
        "CREATE INDEX IF NOT EXISTS matches_intro_idx ON matches(intro_id)",
    ]
    engine = _engine()
    async with engine.begin() as conn:
        for stmt in migrations:
            try:
                await conn.execute(text(stmt))
            except Exception as exc:
                log.warning("migration skipped: %s — %s", stmt[:60], exc)

        # Backfill founder_access_token for any existing jobs that don't have one yet.
        # This runs on every startup but is a no-op when all jobs already have a token.
        try:
            result = await conn.execute(
                text("SELECT id FROM jobs WHERE founder_access_token IS NULL")
            )
            rows = result.fetchall()
            if rows:
                for (job_id,) in rows:
                    token = secrets.token_urlsafe(32)
                    await conn.execute(
                        text("UPDATE jobs SET founder_access_token = :token WHERE id = :id"),
                        {"token": token, "id": job_id},
                    )
                log.info("backfilled founder_access_token for %d existing jobs", len(rows))
        except Exception as exc:
            log.warning("founder_access_token backfill failed (non-critical): %s", exc)
