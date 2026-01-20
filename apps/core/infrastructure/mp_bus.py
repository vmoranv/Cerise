"""
Multiprocess event bus implementation using a shared broker.
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import queue
from collections import defaultdict
from datetime import datetime
from typing import Any

from .event import Event, EventBus, EventHandler
from .mp_broker import BrokerManager

logger = logging.getLogger(__name__)




class MultiProcessMessageBus(EventBus):
    """Async event bus backed by a multiprocess broker."""

    def __init__(self, broker: Any, inbound: Any, manager: BrokerManager | None = None):
        self._broker = broker
        self._queue = inbound
        self._manager = manager
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._running = False
        self._task: asyncio.Task | None = None

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)
        logger.debug("Subscribed to '%s': %s", event_type, handler.__name__)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            return True
        return False

    async def publish(self, event: Event) -> None:
        payload = _event_to_payload(event)
        await asyncio.to_thread(self._broker.publish, payload)
        logger.debug("Published event: %s", event.type)

    def publish_sync(self, event: Event) -> None:
        payload = _event_to_payload(event)
        self._broker.publish(payload)
        logger.debug("Published event: %s", event.type)

    async def emit(self, event_type: str, data: dict | None = None, source: str = "") -> None:
        event = Event(type=event_type, data=data or {}, source=source)
        await self.publish(event)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("MultiProcessMessageBus started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        try:
            self._broker.unregister(self._queue)
        except Exception:
            pass
        logger.info("MultiProcessMessageBus stopped")

    async def wait_empty(self) -> None:
        while True:
            payload = await asyncio.to_thread(_queue_get, self._queue, 0.0)
            if payload is None:
                break
            event = _payload_to_event(payload)
            await self._process_event(event)

    def clear_handlers(self) -> None:
        self._handlers.clear()

    async def _run_loop(self) -> None:
        while self._running:
            payload = await asyncio.to_thread(_queue_get, self._queue, 1.0)
            if payload is None:
                continue
            event = _payload_to_event(payload)
            await self._process_event(event)

    async def _process_event(self, event: Event) -> None:
        matched_handlers: list[EventHandler] = []
        for pattern, handlers in self._handlers.items():
            if _match_event(event.type, pattern):
                matched_handlers.extend(handlers)

        if not matched_handlers:
            logger.debug("No handlers for event: %s", event.type)
            return

        tasks = [handler(event) for handler in matched_handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for handler, result in zip(matched_handlers, results):
            if isinstance(result, Exception):
                logger.exception("Error in handler %s: %s", handler.__name__, result)


def _queue_get(q: Any, timeout: float) -> dict[str, Any] | None:
    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        return None


def _event_to_payload(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "type": event.type,
        "data": event.data,
        "source": event.source,
        "timestamp": event.timestamp.isoformat(),
    }


def _payload_to_event(payload: dict[str, Any]) -> Event:
    timestamp = payload.get("timestamp")
    if isinstance(timestamp, str):
        try:
            parsed = datetime.fromisoformat(timestamp)
        except ValueError:
            parsed = datetime.now()
    else:
        parsed = datetime.now()
    return Event(
        type=payload.get("type", ""),
        data=payload.get("data", {}) or {},
        source=payload.get("source", ""),
        timestamp=parsed,
        id=payload.get("id", ""),
    )


def _match_event(event_type: str, pattern: str) -> bool:
    return pattern == event_type or fnmatch.fnmatch(event_type, pattern)
