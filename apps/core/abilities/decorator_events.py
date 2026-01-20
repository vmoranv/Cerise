"""Event decorator helpers."""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from ..infrastructure import get_message_bus

if TYPE_CHECKING:
    from ..infrastructure import EventBus

logger = logging.getLogger(__name__)


def on_event(event_type: str, *, bus: EventBus | None = None):
    """
    Decorator to subscribe to message bus events.

    Usage:
        @on_event("dialogue.user_message")
        async def handle_message(event: Event):
            print(f"User said: {event.data['content']}")
    """

    def decorator(func: Callable) -> Callable:
        bus_instance = bus or get_message_bus()
        bus_instance.subscribe(event_type, func)
        logger.debug("Subscribed to event: %s", event_type)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator
