"""
Event handlers for memory ingestion.
"""

from __future__ import annotations

from ..contracts.events import DIALOGUE_ASSISTANT_RESPONSE, DIALOGUE_USER_MESSAGE
from ..infrastructure import Event, EventBus
from ..services.ports import MemoryService


class MemoryEventHandler:
    """Attach dialogue events to memory ingestion."""

    def __init__(self, bus: EventBus, memory: MemoryService):
        self._bus = bus
        self._memory = memory

    def attach(self) -> None:
        """Subscribe to dialogue events."""
        self._bus.subscribe(DIALOGUE_USER_MESSAGE, self._handle_user_message)
        self._bus.subscribe(DIALOGUE_ASSISTANT_RESPONSE, self._handle_assistant_message)

    async def _handle_user_message(self, event: Event) -> None:
        data = event.data or {}
        session_id = data.get("session_id", "")
        content = data.get("content", "")
        if not session_id or not content:
            return
        await self._memory.ingest_message(session_id=session_id, role="user", content=content)

    async def _handle_assistant_message(self, event: Event) -> None:
        data = event.data or {}
        session_id = data.get("session_id", "")
        content = data.get("content", "")
        if not session_id or not content:
            return
        await self._memory.ingest_message(
            session_id=session_id,
            role="assistant",
            content=content,
            metadata={"model": data.get("model", "")},
        )
