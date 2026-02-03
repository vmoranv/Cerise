"""Pydantic models for API payloads."""

from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    session_id: str
    emotion: str
    emotion_intensity: float


class SessionCreate(BaseModel):
    user_id: str = ""
    personality: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    message_count: int


class EmotionUpdate(BaseModel):
    emotion: str
    intensity: float = 1.0


class Live2DParameter(BaseModel):
    id: str
    value: float
    weight: float | None = None


class Live2DParametersUpdate(BaseModel):
    parameters: list[Live2DParameter]
    smoothing: float | None = None


class Live2DEmotionUpdate(BaseModel):
    valence: float
    arousal: float
    intensity: float
    smoothing: float | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
