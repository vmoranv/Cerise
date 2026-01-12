"""
Memory event handlers.
"""

from __future__ import annotations

from ...infrastructure import MessageBus
from .engine import MemoryEngine


class MemoryEventHandler:
    """Attach memory ingestion to the message bus."""

    def __init__(self, engine: MemoryEngine, bus: MessageBus | None = None):
        self._engine = engine
        self._bus = bus or MessageBus()
        if self._engine.bus is None:
            self._engine.bus = self._bus

    def attach(self) -> None:
        """Subscribe to dialogue events."""
        self._bus.subscribe("dialogue.user_message", self._handle_user_message)
        self._bus.subscribe("dialogue.assistant_response", self._handle_assistant_message)

    async def _handle_user_message(self, event):
        data = event.data or {}
        session_id = data.get("session_id", "")
        content = data.get("content", "")
        if not session_id or not content:
            return
        await self._engine.ingest_message(session_id=session_id, role="user", content=content)

    async def _handle_assistant_message(self, event):
        data = event.data or {}
        session_id = data.get("session_id", "")
        content = data.get("content", "")
        if not session_id or not content:
            return
        await self._engine.ingest_message(
            session_id=session_id,
            role="assistant",
            content=content,
            metadata={"model": data.get("model", "")},
        )
