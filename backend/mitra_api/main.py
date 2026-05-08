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

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from mitra_api.agent.orchestrator import run_agent_turn
from mitra_api.agent.session_store import AgentSessionStore, build_session_store
from mitra_api.config import Settings, get_settings
from mitra_api.founder.routes import router as founder_router
from mitra_api.jobs.admin import admin_router
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
    yield
    # Graceful shutdown
    await session_store.aclose()
    # Dispose DB engine connection pool
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp_router)
app.include_router(twilio_whatsapp_router)
app.include_router(admin_router)
app.include_router(founder_router)


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
