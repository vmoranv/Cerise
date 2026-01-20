"""Chat routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from ...ai import DialogueEngine
from ...character import EmotionStateMachine
from ...services.ports import EmotionService
from ..dependencies import get_dialogue_engine, get_emotion_service, get_emotion_state
from ..models import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    dialogue_engine: DialogueEngine = Depends(get_dialogue_engine),
    emotion_service: EmotionService = Depends(get_emotion_service),
    emotion_state: EmotionStateMachine = Depends(get_emotion_state),
) -> ChatResponse:
    """Send a chat message."""
    session = None
    if request.session_id:
        session = dialogue_engine.get_session(request.session_id)

    if not session:
        session = dialogue_engine.create_session()

    try:
        response = await dialogue_engine.chat(
            session=session,
            user_message=request.message,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
        )

        emotion_result = emotion_service.analyze(response)
        emotion_state.set_emotion(
            emotion_result.primary_emotion.value,
            intensity=emotion_result.confidence,
        )

        return ChatResponse(
            response=response,
            session_id=session.id,
            emotion=emotion_state.current_state.value,
            emotion_intensity=emotion_state.current_intensity,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e)) from e
