"""
Event System and Message Bus

Async event-driven publish/subscribe message bus.
"""

import asyncio
import fnmatch
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[["Event"], Coroutine[Any, Any, None]]


@dataclass
class Event:
    """Event data structure"""

    type: str  # e.g., "dialogue.response", "emotion.changed"
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


class MessageBus:
    """Async message bus for event-driven communication"""

    _instance: "MessageBus | None" = None

    def __new__(cls) -> "MessageBus":
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
            self._queue: asyncio.Queue[Event] = asyncio.Queue()
            self._running = False
            self._task: asyncio.Task | None = None

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type

        Supports wildcards: "dialogue.*", "*.changed"
        """
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed to '{event_type}': {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """Unsubscribe from an event type"""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            return True
        return False

    async def publish(self, event: Event) -> None:
        """Publish an event"""
        await self._queue.put(event)
        logger.debug(f"Published event: {event.type}")

    def publish_sync(self, event: Event) -> None:
        """Publish an event synchronously (for non-async contexts)"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(event))
        except RuntimeError:
            # No running loop, create one
            asyncio.run(self.publish(event))

    async def emit(self, event_type: str, data: dict | None = None, source: str = "") -> None:
        """Convenience method to create and publish an event"""
        event = Event(type=event_type, data=data or {}, source=source)
        await self.publish(event)

    async def _process_event(self, event: Event) -> None:
        """Process a single event"""
        matched_handlers: list[EventHandler] = []

        for pattern, handlers in self._handlers.items():
            if fnmatch.fnmatch(event.type, pattern):
                matched_handlers.extend(handlers)

        if not matched_handlers:
            logger.debug(f"No handlers for event: {event.type}")
            return

        # Execute handlers concurrently
        tasks = [handler(event) for handler in matched_handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for handler, result in zip(matched_handlers, results):
            if isinstance(result, Exception):
                logger.exception(f"Error in handler {handler.__name__}: {result}")

    async def _run_loop(self) -> None:
        """Main event loop"""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process_event(event)
                self._queue.task_done()
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def start(self) -> None:
        """Start the message bus"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("MessageBus started")

    async def stop(self) -> None:
        """Stop the message bus"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("MessageBus stopped")

    async def wait_empty(self) -> None:
        """Wait for all events to be processed"""
        await self._queue.join()

    def clear_handlers(self) -> None:
        """Clear all handlers"""
        self._handlers.clear()

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)"""
        if cls._instance:
            cls._instance.clear_handlers()
        cls._instance = None


# Global instance
message_bus = MessageBus()
