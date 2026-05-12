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

    await engine.dispose()
    log.info("Migrations complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(create_all())
