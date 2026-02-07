"""
Event bus factory for the runtime.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from ..config.schemas import BusConfig
from ..infrastructure import EventBus, get_message_bus
from ..infrastructure.mp_broker import get_broker_manager
from ..infrastructure.mp_bus import MultiProcessMessageBus

logger = logging.getLogger(__name__)


def build_event_bus(config: BusConfig) -> EventBus:
    """Build the event bus based on configuration."""
    mode = (config.mode or "local").lower()
    if mode == "multiprocess":
        authkey = (config.auth_key or "cerise").encode()
        manager = get_broker_manager(
            host=config.broker_host,
            port=config.broker_port,
            authkey=authkey,
            start_broker=config.start_broker,
        )
        broker = cast(Any, manager).get_broker()
        inbound = broker.register()
        return MultiProcessMessageBus(broker, inbound, manager)

    if mode != "local":
        logger.warning("Unknown bus mode '%s', falling back to local.", mode)

    return get_message_bus()
