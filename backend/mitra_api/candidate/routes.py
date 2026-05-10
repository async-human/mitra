"""Candidate web chat endpoint — powers the in-app chat UI."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from mitra_api.agent.orchestrator import run_agent_turn
from mitra_api.agent.session_store import AgentSessionStore, build_session_store
from mitra_api.config import Settings, get_settings

log = logging.getLogger(__name__)

router = APIRouter(prefix="/candidate", tags=["candidate"])

_store: AgentSessionStore | None = None


def _get_store(settings: Settings) -> AgentSessionStore:
    global _store
    if _store is None:
        _store = build_session_store(settings)
    return _store


class CandidateChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=200)
    message: str = Field(default="", max_length=4000)
    user_name: str | None = Field(default=None, max_length=100)


class JobCard(BaseModel):
    id: str
    title: str
    description: str  # "Company · 95% fit · Python · Remote"


class CandidateChatResponse(BaseModel):
    reply: str
    job_cards: list[JobCard]


@router.post("/chat", response_model=CandidateChatResponse)
async def candidate_chat(
    body: CandidateChatRequest,
    settings: Settings = Depends(get_settings),
) -> CandidateChatResponse:
    store = _get_store(settings)
    # "web:" prefix keeps web sessions separate from WhatsApp sessions
    sid = f"web:{body.session_id}"
    is_init = not body.message.strip()

    if is_init:
        # On page load: return last assistant message if session exists, else trigger greeting
        transcript = await store.get_transcript(sid)
        if transcript:
            for msg in reversed(transcript):
                if msg.role == "assistant":
                    return CandidateChatResponse(reply=msg.content, job_cards=[])
        name_part = f" The candidate's name is {body.user_name}." if body.user_name else ""
        user_text = (
            f"[CONVERSATION START on the Mitra web app.{name_part} "
            "Greet them warmly by name if you have it, and ask what brings them here.]"
        )
    else:
        user_text = body.message.strip()

    turn = await run_agent_turn(
        whatsapp_sender_id=sid,
        user_text=user_text,
        sessions=store,
        settings=settings,
    )

    job_cards = [
        JobCard(id=r.row_id, title=r.title, description=r.description)
        for r in turn.native_list_rows
    ]

    return CandidateChatResponse(
        reply=turn.history_assistant_text,
        job_cards=job_cards,
    )
