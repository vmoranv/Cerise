"""Operation capture/input factory tests."""

from __future__ import annotations

import numpy as np
import pytest
from apps.core.operation.capture.factory import create_capture
from apps.core.operation.capture.fallback import FallbackCapture
from apps.core.operation.input.factory import create_gamepad, create_interaction, create_policy
from apps.core.operation.input.gamepad import GamepadState


def test_capture_factory_image_loops_frames() -> None:
    frame = np.zeros((12, 34, 3), dtype=np.uint8)
    capture = create_capture("image", images=[frame], loop=True)

    assert capture.connect(123)
    assert capture.width == 34
    assert capture.height == 12

    assert capture.get_frame() is frame
    assert capture.get_frame() is frame


def test_fallback_capture_switches_backend_on_failure() -> None:
    class AlwaysNone:
        def __init__(self) -> None:
            self._connected = False
            self._hwnd = 0

        @property
        def width(self) -> int:
            return 10

        @property
        def height(self) -> int:
            return 20

        @property
        def hwnd(self) -> int:
            return self._hwnd

        def connect(self, hwnd: int) -> bool:
            self._hwnd = hwnd
            self._connected = True
            return True

        def connected(self) -> bool:
            return self._connected

        def get_frame(self):
            return None

        def close(self) -> None:
            self._connected = False

    class ReturnsFrame(AlwaysNone):
        def __init__(self, frame: np.ndarray) -> None:
            super().__init__()
            self._frame = frame

        def get_frame(self):
            return self._frame

    failing = AlwaysNone()
    good_frame = np.ones((2, 3, 3), dtype=np.uint8)
    succeeding = ReturnsFrame(good_frame)

    capture = FallbackCapture([failing, succeeding])
    assert capture.connect(999)

    frame = capture.get_frame()
    assert frame is good_frame
    assert failing.connected() is False
    assert succeeding.connected() is True


def test_interaction_factory_null_backend_is_safe() -> None:
    interaction = create_interaction("null")
    assert interaction.connect(123)
    interaction.click(1, 2, "left")
    interaction.key_press("enter")
    interaction.close()


@pytest.mark.asyncio
async def test_policy_factory_callable_backend() -> None:
    async def predict(frame, meta):  # noqa: ANN001
        assert meta["k"] == "v"
        return GamepadState(axes={"lx": 0.5}, buttons={"a": True})

    policy = create_policy("callable", predict=predict)
    state = await policy.predict(frame=None, meta={"k": "v"})
    assert state.axes["lx"] == 0.5
    assert state.buttons["a"] is True


def test_gamepad_factory_null_backend_is_safe() -> None:
    gamepad = create_gamepad("null")
    assert gamepad.connect()
    gamepad.set_state(GamepadState(axes={"lx": 0.1}, buttons={"a": True}))
    gamepad.close()
