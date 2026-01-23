"""Operation layer event emission tests."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import numpy as np
import pytest
from apps.core.contracts.events import (
    OPERATION_ACTION_COMPLETED,
    OPERATION_INPUT_PERFORMED,
    OPERATION_WINDOW_CONNECTED,
)
from apps.core.infrastructure import Event, MessageBus

CORE_ROOT = Path(__file__).resolve().parents[1]
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from operation.service import OperationService  # noqa: E402
from operation.workflow.actions import ClickAction  # noqa: E402
from operation.workflow.manager import ActionSequence  # noqa: E402


class DummyCapture:
    def __init__(self, width: int = 640, height: int = 480) -> None:
        self._width = width
        self._height = height
        self._hwnd = 0
        self._connected = False

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def hwnd(self) -> int:
        return self._hwnd

    def connect(self, hwnd: int) -> bool:
        self._hwnd = hwnd
        self._connected = True
        return True

    def connected(self) -> bool:
        return self._connected

    def get_frame(self) -> np.ndarray:
        return np.zeros((self._height, self._width, 3), dtype=np.uint8)

    def close(self) -> None:
        self._connected = False
        self._hwnd = 0


class DummyInteraction:
    def __init__(self) -> None:
        self._hwnd = 0
        self._connected = False

    @property
    def hwnd(self) -> int:
        return self._hwnd

    def connect(self, hwnd: int) -> bool:
        self._hwnd = hwnd
        self._connected = True
        return True

    def connected(self) -> bool:
        return self._connected

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        return None

    def close(self) -> None:
        self._connected = False
        self._hwnd = 0


@pytest.mark.asyncio
async def test_operation_emits_window_and_input_events() -> None:
    MessageBus.reset()
    bus = MessageBus()
    await bus.start()

    seen: dict[str, dict] = {}
    done = asyncio.Event()

    async def capture(event: Event) -> None:
        seen[event.type] = event.data
        if OPERATION_WINDOW_CONNECTED in seen and OPERATION_INPUT_PERFORMED in seen:
            done.set()

    bus.subscribe(OPERATION_WINDOW_CONNECTED, capture)
    bus.subscribe(OPERATION_INPUT_PERFORMED, capture)

    service = OperationService(capture=DummyCapture(), interaction=DummyInteraction(), bus=bus)

    assert service.connect(123)
    service.click(10, 20, "left")

    await asyncio.wait_for(done.wait(), timeout=2)
    await bus.wait_empty()
    await bus.stop()
    MessageBus.reset()

    assert seen[OPERATION_WINDOW_CONNECTED]["hwnd"] == 123
    assert seen[OPERATION_INPUT_PERFORMED]["action"] == "click"


@pytest.mark.asyncio
async def test_operation_emits_action_completed() -> None:
    MessageBus.reset()
    bus = MessageBus()
    await bus.start()

    captured: dict[str, dict] = {}
    done = asyncio.Event()

    async def capture(event: Event) -> None:
        captured[event.type] = event.data
        done.set()

    bus.subscribe(OPERATION_ACTION_COMPLETED, capture)

    service = OperationService(capture=DummyCapture(), interaction=DummyInteraction(), bus=bus)
    assert service.connect(123)

    sequence = ActionSequence(name="test").add(ClickAction(x=5, y=6))
    sequence.execute(service)

    await asyncio.wait_for(done.wait(), timeout=2)
    await bus.wait_empty()
    await bus.stop()
    MessageBus.reset()

    assert captured[OPERATION_ACTION_COMPLETED]["action"] == "Click"
    assert captured[OPERATION_ACTION_COMPLETED]["status"] == "success"
