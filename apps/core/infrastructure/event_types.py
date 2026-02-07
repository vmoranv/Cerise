"""Event and bus type definitions."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

# Type alias for event handlers
EventHandler = Callable[["Event"], Coroutine[Any, Any, None]]


@dataclass
class Event:
    """Event data structure."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


class EventBus(Protocol):
    """Protocol for event bus implementations."""

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type."""

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """Unsubscribe from an event type."""

    async def publish(self, event: Event) -> None:
        """Publish an event."""

    def publish_sync(self, event: Event) -> None:
        """Publish an event synchronously."""

    async def emit(self, event_type: str, data: dict[str, Any] | None = None, source: str = "") -> None:
        """Create and publish an event."""

    async def start(self) -> None:
        """Start processing events."""

    async def stop(self) -> None:
        """Stop processing events."""

    async def wait_empty(self) -> None:
        """Wait for the queue to drain."""

    def clear_handlers(self) -> None:
        """Clear all handlers."""
