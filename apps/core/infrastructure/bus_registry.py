"""Default bus registry helpers."""

from __future__ import annotations

from .event_types import EventBus
from .message_bus import MessageBus

_DEFAULT_BUS: EventBus | None = None


def set_default_bus(bus: EventBus) -> None:
    """Set the process-wide default event bus."""
    global _DEFAULT_BUS
    _DEFAULT_BUS = bus


def get_default_bus() -> EventBus | None:
    """Return the process-wide default bus if set."""
    return _DEFAULT_BUS


def get_message_bus() -> EventBus:
    """Return the default event bus (or the local singleton)."""
    return _DEFAULT_BUS or MessageBus()
