"""API route modules."""

from .agents import router as agents_router
from .chat import router as chat_router
from .emotion import router as emotion_router
from .health import router as health_router
from .live2d import router as live2d_router
from .openai import router as openai_router
from .sessions import router as sessions_router
from .skills import router as skills_router
from .websocket import router as websocket_router

__all__ = [
    "agents_router",
    "chat_router",
    "emotion_router",
    "health_router",
    "live2d_router",
    "openai_router",
    "sessions_router",
    "skills_router",
    "websocket_router",
]
