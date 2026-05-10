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
    """
    from sqlalchemy import text
    migrations = [
        # Intro.response_token — one-click founder reply token
        "ALTER TABLE intros ADD COLUMN IF NOT EXISTS response_token VARCHAR(64)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_intros_response_token ON intros(response_token) WHERE response_token IS NOT NULL",
        # Job.founder_access_token — persistent no-login founder portal token
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS founder_access_token VARCHAR(64)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_jobs_founder_access_token ON jobs(founder_access_token) WHERE founder_access_token IS NOT NULL",
    ]
    engine = _engine()
    async with engine.begin() as conn:
        for stmt in migrations:
            try:
                await conn.execute(text(stmt))
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("migration skipped: %s — %s", stmt[:60], exc)
