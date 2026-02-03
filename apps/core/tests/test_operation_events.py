"""Operation layer event emission tests."""

from __future__ import annotations

import asyncio

import numpy as np
import pytest
from apps.core.contracts.events import (
    OPERATION_ACTION_COMPLETED,
    OPERATION_INPUT_PERFORMED,
    OPERATION_WINDOW_CONNECTED,
)
from apps.core.infrastructure import Event, MessageBus
from apps.core.operation.input.gamepad import GamepadState
from apps.core.operation.service import OperationService
from apps.core.operation.workflow.actions import Action, ClickAction, WaitAction
from apps.core.operation.workflow.manager import ActionSequence
from apps.core.operation.workflow.types import ActionResult, ActionStatus, CancelToken


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
        self.clicks: list[tuple[int, int, str]] = []

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
        if x is None or y is None:
            return None
        self.clicks.append((x, y, button))
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


@pytest.mark.asyncio
async def test_operation_emits_gamepad_input_events() -> None:
    MessageBus.reset()
    bus = MessageBus()
    await bus.start()

    captured: list[dict] = []
    done = asyncio.Event()

    async def capture(event: Event) -> None:
        captured.append(event.data)
        if any(item.get("action") == "gamepad.button" for item in captured):
            done.set()

    bus.subscribe(OPERATION_INPUT_PERFORMED, capture)

    service = OperationService(capture=DummyCapture(), interaction=DummyInteraction(), bus=bus)
    assert service.connect(123)
    service.gamepad_button("a", True)

    await asyncio.wait_for(done.wait(), timeout=2)
    await bus.wait_empty()
    await bus.stop()
    MessageBus.reset()

    assert any(item.get("action") == "gamepad.button" for item in captured)


class DummyPolicy:
    async def predict(self, *, frame=None, meta=None) -> GamepadState:  # noqa: ANN001,ARG002
        return GamepadState(axes={"lx": 0.25}, buttons={"a": True})


@pytest.mark.asyncio
async def test_operation_emits_gamepad_policy_events() -> None:
    MessageBus.reset()
    bus = MessageBus()
    await bus.start()

    captured: list[dict] = []
    done = asyncio.Event()

    async def capture(event: Event) -> None:
        captured.append(event.data)
        if any(item.get("action") == "gamepad.policy" for item in captured):
            done.set()

    bus.subscribe(OPERATION_INPUT_PERFORMED, capture)

    service = OperationService(
        capture=DummyCapture(),
        interaction=DummyInteraction(),
        policy=DummyPolicy(),
        bus=bus,
    )
    assert service.connect(123)
    state = await service.gamepad_policy_step(meta={"source": "test"})
    assert state.buttons.get("a") is True

    await asyncio.wait_for(done.wait(), timeout=2)
    await bus.wait_empty()
    await bus.stop()
    MessageBus.reset()

    event = next(item for item in captured if item.get("action") == "gamepad.policy")
    assert event["params"]["meta"]["source"] == "test"


class CancelAction(Action):
    def __init__(self, reason: str = "cancel") -> None:
        super().__init__(name="Cancel")
        self.reason = reason

    def execute(self, service: OperationService, cancel_token: CancelToken | None = None) -> ActionResult:
        if cancel_token:
            cancel_token.cancel(self.reason)
        return ActionResult(ActionStatus.SUCCESS, "cancel requested")


def test_action_sequence_cancellation_skips_next_action() -> None:
    interaction = DummyInteraction()
    service = OperationService(capture=DummyCapture(), interaction=interaction, bus=None)
    assert service.connect(123)

    token = CancelToken()
    sequence = ActionSequence(name="cancel-test").add(CancelAction("stop")).add(ClickAction(x=5, y=6))
    results = sequence.execute(service, cancel_token=token)

    assert token.cancelled is True
    assert len(results) == 2
    assert results[0].status == ActionStatus.SUCCESS
    assert results[1].status == ActionStatus.SKIPPED
    assert interaction.clicks == []


def test_action_sequence_timeout_prevents_followup_action() -> None:
    interaction = DummyInteraction()
    service = OperationService(capture=DummyCapture(), interaction=interaction, bus=None)
    assert service.connect(123)

    sequence = ActionSequence(name="timeout-test").add(WaitAction(duration=0.02)).add(ClickAction(x=5, y=6))
    results = sequence.execute(service, timeout=0.001)

    assert len(results) == 2
    assert results[0].status == ActionStatus.SUCCESS
    assert results[1].status == ActionStatus.TIMEOUT
    assert interaction.clicks == []


def test_click_action_scales_base_coordinates() -> None:
    interaction = DummyInteraction()
    capture = DummyCapture(width=640, height=480)
    service = OperationService(capture=capture, interaction=interaction, bus=None)
    assert service.connect(123)

    # Center of 1920x1080 should map to center of 640x480.
    action = ClickAction(x=960, y=540, base_width=1920, base_height=1080)
    results = ActionSequence(name="scale-test").add(action).execute(service)

    assert len(results) == 1
    assert results[0].status == ActionStatus.SUCCESS
    assert interaction.clicks == [(320, 240, "left")]
