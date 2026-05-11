"""
mitra_api/main.py  (updated for production)

Adds:
  - Admin router (/admin/jobs/*)
  - DB healthcheck in /readyz
  - Graceful DB engine disposal on shutdown
"""

import logging
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from mitra_api.agent.orchestrator import run_agent_turn
from mitra_api.agent.session_store import AgentSessionStore, build_session_store
from mitra_api.config import Settings, get_settings
from mitra_api.candidate.routes import router as candidate_router
from mitra_api.founder.routes import router as founder_router
from mitra_api.jobs.admin import admin_router, admin_meta_router
from mitra_api.llm.factory import get_llm_adapter
from mitra_api.llm.types import ChatMessage, ToolDefinition
from mitra_api.twilio_whatsapp.routes import router as twilio_whatsapp_router
from mitra_api.whatsapp.routes import router as whatsapp_router

logging.basicConfig(level=logging.INFO)

session_store = build_session_store(get_settings())


def get_sessions() -> AgentSessionStore:
    return session_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run schema migrations on startup (idempotent ADD COLUMN IF NOT EXISTS)
    try:
        from mitra_api.db.engine import run_schema_migrations
        await run_schema_migrations()
    except Exception:
        pass  # DB may not be configured in all envs

    yield

    # Graceful shutdown
    await session_store.aclose()
    try:
        from mitra_api.db.engine import _engine
        engine = _engine()
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(title="Mitra API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # cannot be True when allow_origins=["*"] — browsers reject it
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp_router)
app.include_router(twilio_whatsapp_router)
app.include_router(admin_router)
app.include_router(admin_meta_router)
app.include_router(founder_router)
app.include_router(candidate_router)


@app.get("/healthz", response_class=PlainTextResponse)
async def healthz() -> str:
    return "ok"


@app.get("/readyz")
async def readyz(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Checks LLM connectivity and DB reachability."""
    result: dict[str, Any] = {}

    # LLM check
    try:
        get_llm_adapter(settings)
        result["llm"] = {"ok": True, "provider": settings.mitra_llm_provider}
    except Exception as exc:
        result["llm"] = {"ok": False, "error": str(exc)}

    # DB check
    if settings.mitra_database_url:
        try:
            from sqlalchemy import text
            from mitra_api.db.engine import get_session_factory
            factory = get_session_factory()
            async with factory() as db:
                await db.execute(text("SELECT 1"))
            result["db"] = {"ok": True}
        except Exception as exc:
            result["db"] = {"ok": False, "error": str(exc)}
    else:
        result["db"] = {"ok": False, "error": "MITRA_DATABASE_URL not set"}

    return result


@app.delete("/admin/candidates/{phone}/reset")
async def reset_candidate(
    phone: str,
    x_admin_key: str = Header(default=""),
    settings: Settings = Depends(get_settings),
    store: AgentSessionStore = Depends(get_sessions),
) -> dict[str, Any]:
    """
    Wipe all history for a candidate — Redis session + Postgres rows.
    Useful for test resets. Requires X-Admin-Key header.
    Phone must be E.164 format: %2B919405109606 (URL-encode the +).
    """
    expected = (getattr(settings, "mitra_admin_key", "") or "").strip()
    if not expected or x_admin_key != expected:
        raise HTTPException(403, "Invalid admin key")

    # normalise: accept +91... or 91... or URL-encoded %2B91...
    sid = phone.strip()
    if not sid.startswith("+"):
        sid = "+" + sid

    deleted: dict[str, Any] = {"phone": sid}

    # ── Redis ─────────────────────────────────────────────────────────────────
    try:
        pfx = getattr(settings, "mitra_redis_key_prefix", "mitra") or "mitra"
        raw_store = store  # RedisAgentSessionStore or InMemory
        if hasattr(raw_store, "_r"):
            r = raw_store._r
            msgs_key = f"{pfx}:session:{sid}:msgs"
            sigs_key = f"{pfx}:session:{sid}:signals"
            deleted["redis_msgs"]    = await r.delete(msgs_key)
            deleted["redis_signals"] = await r.delete(sigs_key)
        else:
            # InMemoryAgentSessionStore
            raw_store._history.pop(sid, None)
            raw_store._signals.pop(sid, None)
            deleted["redis_msgs"] = deleted["redis_signals"] = "in-memory cleared"
    except Exception as exc:
        deleted["redis_error"] = str(exc)

    # ── Postgres ──────────────────────────────────────────────────────────────
    try:
        from sqlalchemy import delete as sa_delete, select as sa_select
        from mitra_api.db.engine import get_session_factory
        from mitra_api.db.models import Candidate

        factory = get_session_factory()
        async with factory() as db:
            row = (await db.execute(
                sa_select(Candidate).where(Candidate.phone == sid)
            )).scalar_one_or_none()

            if row:
                await db.delete(row)   # cascades to candidate_signals + intros
                await db.commit()
                deleted["postgres"] = "candidate + signals + intros deleted"
            else:
                deleted["postgres"] = "no candidate row found"
    except Exception as exc:
        deleted["postgres_error"] = str(exc)

    return deleted


@app.post("/debug/agent")
async def debug_agent(
    message: Annotated[str, Query(..., min_length=1)],
    settings: Settings = Depends(get_settings),
    store: AgentSessionStore = Depends(get_sessions),
    session_id: Annotated[str, Query()] = "debug-user",
) -> dict[str, Any]:
    """Test the full agent loop without WhatsApp."""
    turn = await run_agent_turn(
        whatsapp_sender_id=session_id,
        user_text=message,
        sessions=store,
        settings=settings,
    )
    return {
        "reply":                    turn.history_assistant_text,
        "native_list_rows":         [{"id": r.row_id, "title": r.title} for r in turn.native_list_rows],
        "fallback_plain_segments":  len(turn.whatsapp_fallback_plain_parts),
    }


@app.post("/debug/llm")
async def debug_llm(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    adapter = get_llm_adapter(settings)
    out = await adapter.complete(
        model=settings.mitra_llm_model,
        messages=[
            ChatMessage(role="system", content="You are a terse test harness."),
            ChatMessage(role="user",   content="Reply with one word: ready"),
        ],
        tools=[],
        max_tokens=20,
        temperature=0.0,
    )
    return {"content": out.content}
