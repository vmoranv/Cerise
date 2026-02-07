"""Session management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ...ai import DialogueEngine
from ...character import PersonalityModel
from ..dependencies import get_dialogue_engine, get_personality
from ..models import SessionCreate, SessionResponse

router = APIRouter()


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreate,
    dialogue_engine: DialogueEngine = Depends(get_dialogue_engine),
    personality: PersonalityModel = Depends(get_personality),
) -> SessionResponse:
    """Create a new conversation session."""
    system_prompt = personality.generate_system_prompt() if personality else ""

    session = dialogue_engine.create_session(
        user_id=request.user_id,
        system_prompt=system_prompt,
    )

    return SessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        message_count=len(session.messages),
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    dialogue_engine: DialogueEngine = Depends(get_dialogue_engine),
) -> SessionResponse:
    """Get session info."""
    session = dialogue_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        message_count=len(session.messages),
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    dialogue_engine: DialogueEngine = Depends(get_dialogue_engine),
) -> dict[str, Any]:
    """Delete a session."""
    if dialogue_engine.delete_session(session_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")
