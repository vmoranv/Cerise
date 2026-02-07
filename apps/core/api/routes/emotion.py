"""Emotion routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ...character import EmotionStateMachine
from ..dependencies import get_emotion_state
from ..models import EmotionUpdate

router = APIRouter()


@router.get("/emotion")
async def get_emotion(emotion_state: EmotionStateMachine = Depends(get_emotion_state)) -> dict[str, Any]:
    """Get current emotion state."""
    return emotion_state.get_animation_params()


@router.post("/emotion")
async def set_emotion(
    request: EmotionUpdate,
    emotion_state: EmotionStateMachine = Depends(get_emotion_state),
) -> dict[str, Any]:
    """Manually set emotion state."""
    emotion_state.set_emotion(request.emotion, request.intensity)
    return emotion_state.get_animation_params()
