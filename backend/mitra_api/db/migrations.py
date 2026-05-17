"""
mitra_api/db/migrations.py

Creates all tables + pgvector extension.
Run once before starting the server:

    python -m mitra_api.db.migrations

Or call create_all() from your startup script.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from mitra_api.config import get_settings
from mitra_api.db.engine import _as_async_database_url
from mitra_api.db.models import Base

log = logging.getLogger(__name__)

# Embedding dimensions — must match the model used in tools/embeddings.py
EMBEDDING_DIM = 1536  # text-embedding-3-small  (use 3072 for text-embedding-3-large)


async def create_all() -> None:
    settings = get_settings()
    url = settings.mitra_database_url
    if not url:
        raise RuntimeError("MITRA_DATABASE_URL not set")

    engine = create_async_engine(_as_async_database_url(url), echo=True)

    async with engine.begin() as conn:
        # pgvector extension — must be installed on Postgres (available on Supabase, Neon, etc.)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        log.info("pgvector extension ready")

        # Create all tables from SQLAlchemy models
        await conn.run_sync(Base.metadata.create_all)
        log.info("All tables created")

        # Stage timestamps on intros — track time-to-hire funnel
        for col in ("interview_at", "offer_at", "hired_at"):
            await conn.execute(text(f"""
                ALTER TABLE intros
                ADD COLUMN IF NOT EXISTS {col} TIMESTAMPTZ
            """))
        log.info("intros stage timestamp columns ready")

        # Structured details for interview and offer stages
        for col in ("interview_details", "offer_details"):
            await conn.execute(text(f"""
                ALTER TABLE intros
                ADD COLUMN IF NOT EXISTS {col} JSONB
            """))
        log.info("intros detail JSONB columns ready")

        # Add the actual vector column to job_embeddings
        # (SQLAlchemy doesn't have a native pgvector column type yet)
        await conn.execute(text(f"""
            ALTER TABLE job_embeddings
            ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIM})
        """))
        log.info("job_embeddings.embedding vector column ready (dim=%d)", EMBEDDING_DIM)

        # IVFFlat index for fast approximate nearest-neighbour search
        # cosine distance is best for text embeddings
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS job_embeddings_cosine_idx
            ON job_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 50)
        """))
        log.info("IVFFlat cosine index created on job_embeddings")

        # decline_reason on intros — founder's stated reason when they decline
        await conn.execute(text("""
            ALTER TABLE intros
            ADD COLUMN IF NOT EXISTS decline_reason TEXT
        """))
        log.info("intros.decline_reason column ready")

        # decline_reason_code — structured enumerated pass category for machine-readable signal
        await conn.execute(text("""
            ALTER TABLE intros
            ADD COLUMN IF NOT EXISTS decline_reason_code VARCHAR(40)
        """))
        log.info("intros.decline_reason_code column ready")

        # matches table — every recommendation decision, gated or sent
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS matches (
                id             SERIAL PRIMARY KEY,
                candidate_id   INTEGER NOT NULL REFERENCES candidates(id),
                job_id         INTEGER NOT NULL REFERENCES jobs(id),
                intro_id       INTEGER REFERENCES intros(id),

                salary_fit     FLOAT,
                location_fit   FLOAT,
                skill_fit      FLOAT,
                overall_fit    FLOAT,

                reranker_rank    INTEGER,
                reranker_fit_pct INTEGER,
                reranker_why     TEXT,

                intro_sent   BOOLEAN NOT NULL DEFAULT FALSE,
                gate_blocked BOOLEAN NOT NULL DEFAULT FALSE,
                gate_missing JSONB,

                founder_action   VARCHAR(30),
                founder_feedback TEXT,

                matched_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                decided_at  TIMESTAMPTZ
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS matches_candidate_idx ON matches(candidate_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS matches_job_idx ON matches(job_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS matches_intro_idx ON matches(intro_id)"))
        log.info("matches table and indexes ready")

    await engine.dispose()
    log.info("Migrations complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(create_all())
