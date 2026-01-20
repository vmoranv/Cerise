"""API route modules."""

from .chat import router as chat_router
from .emotion import router as emotion_router
from .health import router as health_router
from .live2d import router as live2d_router
from .sessions import router as sessions_router
from .websocket import router as websocket_router

__all__ = [
    "chat_router",
    "emotion_router",
    "health_router",
    "live2d_router",
    "sessions_router",
    "websocket_router",
]
