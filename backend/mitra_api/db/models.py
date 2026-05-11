"""
mitra_api/db/models.py

PostgreSQL schema. Run migrations with:
    python -m mitra_api.db.migrations

Tables
------
candidates          one row per WhatsApp sender (+91XXXXXXXXXX)
candidate_signals   key-value facts extracted during conversation
jobs                the real job catalogue — managed via admin API
job_embeddings      pgvector embedding per job for semantic search
intros              every introduction Mitra sends, with outcome tracking
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── CANDIDATES ────────────────────────────────────────────────────────────────

class Candidate(Base):
    __tablename__ = "candidates"

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone:           Mapped[str]      = mapped_column(String(32),  unique=True, nullable=False, index=True)
    name:            Mapped[str|None] = mapped_column(String(200))
    current_role:    Mapped[str|None] = mapped_column(String(200))
    current_company: Mapped[str|None] = mapped_column(String(200))
    years_exp:       Mapped[int|None] = mapped_column(Integer)
    resume_text:     Mapped[str|None] = mapped_column(Text)   # extracted from WhatsApp PDF
    created_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active:       Mapped[bool]     = mapped_column(Boolean, default=True)

    signals: Mapped[list[CandidateSignal]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    intros: Mapped[list[Intro]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class CandidateSignal(Base):
    """
    Durable facts per candidate, extracted by the agent during conversation.

    Examples
    --------
    key                  value (JSONB — can be str, int, list, bool)
    -------------------  -------------------------------------------------
    primary_stack        ["Python", "FastAPI", "PostgreSQL"]
    motivation           "wants to build 0→1, tired of maintenance work"
    salary_floor_lpa     30
    salary_target_lpa    45
    location_preference  ["Remote", "Bengaluru"]
    startup_stage_pref   ["Series A", "Series B"]
    dealbreakers         ["crypto", "bond periods > 1 year"]
    notice_period_days   60
    actively_looking     true
    years_experience     6
    """
    __tablename__ = "candidate_signals"
    __table_args__ = (
        UniqueConstraint("candidate_id", "key", name="uq_candidate_signal"),
    )

    id:           Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int]      = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    key:          Mapped[str]      = mapped_column(String(100), nullable=False)
    value:        Mapped[Any]      = mapped_column(JSONB, nullable=False)
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate: Mapped[Candidate] = relationship(back_populates="signals")


# ── JOBS ──────────────────────────────────────────────────────────────────────

class JobStatus(str, enum.Enum):
    active  = "active"
    paused  = "paused"   # company asked to pause
    filled  = "filled"
    expired = "expired"


class Job(Base):
    __tablename__ = "jobs"

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id:   Mapped[str|None] = mapped_column(String(100), unique=True)  # your own ref
    status:        Mapped[str]      = mapped_column(String(20), default=JobStatus.active, index=True)

    # Core fields
    title:         Mapped[str]      = mapped_column(String(300), nullable=False)
    company:       Mapped[str]      = mapped_column(String(200), nullable=False)
    stage:         Mapped[str|None] = mapped_column(String(100))  # "Series A", "Series B"
    sector:        Mapped[str|None] = mapped_column(String(100))  # "Fintech", "B2B SaaS"
    location:      Mapped[str|None] = mapped_column(String(200))
    remote_policy: Mapped[str|None] = mapped_column(String(50))   # "remote", "hybrid", "onsite"
    employment:    Mapped[str|None] = mapped_column(String(50))   # "full_time", "contract"

    # Compensation
    salary_min_lpa: Mapped[int|None] = mapped_column(Integer)
    salary_max_lpa: Mapped[int|None] = mapped_column(Integer)

    # Rich content
    stack:          Mapped[Any|None] = mapped_column(JSONB)   # ["Python", "FastAPI"]
    signals:        Mapped[Any|None] = mapped_column(JSONB)   # ["backend-heavy", "fintech"]
    summary:        Mapped[str|None] = mapped_column(Text)    # shown in card "why"
    full_jd:        Mapped[str|None] = mapped_column(Text)    # full job description

    # Founder contact — for warm intro
    founder_name:   Mapped[str|None] = mapped_column(String(200))
    founder_email:  Mapped[str|None] = mapped_column(String(200))
    founder_wa:     Mapped[str|None] = mapped_column(String(50))  # WA number for intro

    # Founder portal — persistent token that gives no-login access to /founder/portal
    founder_access_token: Mapped[str|None] = mapped_column(String(64), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    embedding: Mapped[JobEmbedding|None] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    intros: Mapped[list[Intro]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobEmbedding(Base):
    """
    pgvector embedding for each job — generated from title + stack + summary.
    Stored separately so the jobs table stays lean.
    """
    __tablename__ = "job_embeddings"

    id:         Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id:     Mapped[int]   = mapped_column(ForeignKey("jobs.id"), unique=True, nullable=False)
    model:      Mapped[str]   = mapped_column(String(100), nullable=False)  # embedding model used
    dimensions: Mapped[int]   = mapped_column(Integer, nullable=False)
    # The actual vector is stored as a native pgvector column — added via raw DDL in migrations
    # because SQLAlchemy doesn't have a built-in type for it yet.
    # Column name: embedding  type: vector(dimensions)

    job: Mapped[Job] = relationship(back_populates="embedding")


# ── INTROS ────────────────────────────────────────────────────────────────────

class IntroStatus(str, enum.Enum):
    sent         = "sent"
    acknowledged = "acknowledged"   # founder replied
    interview    = "interview"       # interview booked
    offer        = "offer"
    hired        = "hired"
    declined     = "declined"
    ghosted      = "ghosted"        # no reply after 7 days


class Intro(Base):
    """Every introduction Mitra makes — the core metric of the whole business."""
    __tablename__ = "intros"

    id:             Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id:   Mapped[int]      = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    job_id:         Mapped[int]      = mapped_column(ForeignKey("jobs.id"),       nullable=False, index=True)
    status:         Mapped[str]      = mapped_column(String(30), default=IntroStatus.sent, index=True)
    intro_note:     Mapped[str|None] = mapped_column(Text)          # the actual intro message sent
    response_token: Mapped[str|None] = mapped_column(String(64), unique=True, index=True)  # one-click reply
    requested_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    interview_at:   Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    offer_at:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    hired_at:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    updated_at:     Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate: Mapped[Candidate] = relationship(back_populates="intros")
    job:       Mapped[Job]       = relationship(back_populates="intros")


# ── SALARY BENCHMARKS ─────────────────────────────────────────────────────────

class SalaryBenchmark(Base):
    """
    Updatable salary benchmarks for India startup roles.
    Seeded from survey data; queryable by admin API.
    Primary source of truth is the jobs table itself — this is the fallback.
    """
    __tablename__ = "salary_benchmarks"
    __table_args__ = (
        UniqueConstraint("role_category", "stage", "seniority", name="uq_salary_benchmark"),
    )

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_category: Mapped[str]      = mapped_column(String(60),  nullable=False, index=True)
    stage:         Mapped[str]      = mapped_column(String(30),  nullable=False, index=True)
    seniority:     Mapped[str]      = mapped_column(String(30),  nullable=False, index=True)
    p25_lpa:       Mapped[int]      = mapped_column(Integer, nullable=False)
    median_lpa:    Mapped[int]      = mapped_column(Integer, nullable=False)
    p75_lpa:       Mapped[int]      = mapped_column(Integer, nullable=False)
    source:        Mapped[str|None] = mapped_column(String(200))  # e.g. "Levels.fyi India 2025-Q1"
    updated_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
