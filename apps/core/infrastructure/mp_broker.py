"""Multiprocess event broker utilities."""

from __future__ import annotations

import logging
import queue
import threading
from multiprocessing.managers import SyncManager
from typing import Any

logger = logging.getLogger(__name__)


class EventBroker:
    """Shared broker that fans out events to per-process queues."""

    def __init__(self) -> None:
        self._queues: list[queue.Queue] = []
        self._lock = threading.Lock()

    def register(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._queues.append(q)
        return q

    def unregister(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._queues:
                self._queues.remove(q)

    def publish(self, payload: dict[str, Any]) -> None:
        with self._lock:
            targets = list(self._queues)
        for q in targets:
            q.put(payload)


_BROKER = EventBroker()


class BrokerManager(SyncManager):
    """Manager hosting the broker instance."""


BrokerManager.register("get_broker", callable=lambda: _BROKER)


def _connect_manager(host: str, port: int, authkey: bytes) -> BrokerManager:
    manager = BrokerManager(address=(host, port), authkey=authkey)
    manager.connect()
    return manager


def _start_manager(host: str, port: int, authkey: bytes) -> BrokerManager:
    manager = BrokerManager(address=(host, port), authkey=authkey)
    manager.start()
    return manager


def get_broker_manager(
    *,
    host: str,
    port: int,
    authkey: bytes,
    start_broker: bool,
) -> BrokerManager:
    """Connect to an existing broker or start one if configured."""
    if start_broker:
        try:
            return _connect_manager(host, port, authkey)
        except OSError:
            logger.info("Starting event broker at %s:%s", host, port)
            return _start_manager(host, port, authkey)
    return _connect_manager(host, port, authkey)
