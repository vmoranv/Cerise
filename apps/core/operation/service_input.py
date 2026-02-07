"""Input-related mixin for operation service."""

from __future__ import annotations

import numpy as np
from apps.core.contracts.events import OPERATION_INPUT_PERFORMED, build_operation_input_performed

from .capture.base import CaptureMethod
from .input.base import Interaction
from .input.gamepad import Gamepad, GamepadState
from .input.policy import GamepadPolicy
from .vision.box import Box


class OperationInputMixin:
    """Input interaction helpers."""

    _interaction: Interaction
    _gamepad: Gamepad
    _capture: CaptureMethod
    _policy: GamepadPolicy
    _hwnd: int

    def _publish_event(self, event_type: str, data: dict[str, object]) -> None:
        raise NotImplementedError

    @staticmethod
    def _box_payload(box: Box) -> dict[str, object]:
        raise NotImplementedError

    def find_template(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        frame: np.ndarray | None = None,
        region: Box | None = None,
        name: str | None = None,
    ) -> Box | None:
        raise NotImplementedError

    def wait_template(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        timeout: float = 10.0,
        interval: float = 0.1,
        region: Box | None = None,
        name: str | None = None,
    ) -> Box | None:
        raise NotImplementedError

    def click(self, x: int, y: int, button: str = "left") -> None:
        """Click a coordinate."""
        self._interaction.click(x, y, button)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="click",
                hwnd=self._hwnd,
                params={"x": x, "y": y, "button": button},
            ),
        )

    def click_box(
        self,
        box: Box,
        button: str = "left",
        relative_x: float = 0.5,
        relative_y: float = 0.5,
    ) -> None:
        """Click within a box."""
        self._interaction.click_box(box, button, relative_x, relative_y)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="click_box",
                hwnd=self._hwnd,
                params={
                    "box": self._box_payload(box),
                    "button": button,
                    "relative_x": relative_x,
                    "relative_y": relative_y,
                },
            ),
        )

    def double_click(self, x: int, y: int, button: str = "left") -> None:
        """Double click a coordinate."""
        self._interaction.double_click(x, y, button)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="double_click",
                hwnd=self._hwnd,
                params={"x": x, "y": y, "button": button},
            ),
        )

    def move(self, x: int, y: int) -> None:
        """Move the mouse."""
        self._interaction.move(x, y)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="move",
                hwnd=self._hwnd,
                params={"x": x, "y": y},
            ),
        )

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        button: str = "left",
        duration: float = 0.0,
    ) -> None:
        """Drag between two coordinates."""
        self._interaction.drag(from_x, from_y, to_x, to_y, button, duration)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="drag",
                hwnd=self._hwnd,
                params={
                    "from_x": from_x,
                    "from_y": from_y,
                    "to_x": to_x,
                    "to_y": to_y,
                    "button": button,
                    "duration": duration,
                },
            ),
        )

    def scroll(self, x: int, y: int, delta: int) -> None:
        """Scroll the mouse wheel."""
        self._interaction.scroll(x, y, delta)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="scroll",
                hwnd=self._hwnd,
                params={"x": x, "y": y, "delta": delta},
            ),
        )

    def key_press(self, key: str, duration: float = 0.0) -> None:
        """Press and release a key."""
        self._interaction.key_press(key, duration)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="key_press",
                hwnd=self._hwnd,
                params={"key": key, "duration": duration},
            ),
        )

    def key_down(self, key: str) -> None:
        """Press a key down."""
        self._interaction.key_down(key)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="key_down",
                hwnd=self._hwnd,
                params={"key": key},
            ),
        )

    def key_up(self, key: str) -> None:
        """Release a key."""
        self._interaction.key_up(key)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="key_up",
                hwnd=self._hwnd,
                params={"key": key},
            ),
        )

    def type_text(self, text: str, interval: float = 0.0) -> None:
        """Type text."""
        self._interaction.type_text(text, interval)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="type_text",
                hwnd=self._hwnd,
                params={"text": text, "interval": interval},
            ),
        )

    def hotkey(self, *keys: str) -> None:
        """Send a hotkey combo."""
        self._interaction.hotkey(*keys)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="hotkey",
                hwnd=self._hwnd,
                params={"keys": list(keys)},
            ),
        )

    # ========== Gamepad ==========

    def gamepad_button(self, button: str, pressed: bool) -> None:
        """Set a gamepad button state."""
        self._gamepad.set_button(button, pressed)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="gamepad.button",
                hwnd=self._hwnd,
                params={"button": str(button), "pressed": bool(pressed)},
            ),
        )

    def gamepad_axis(self, axis: str, value: float) -> None:
        """Set a gamepad axis value (normalized -1..1)."""
        self._gamepad.set_axis(axis, float(value))
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="gamepad.axis",
                hwnd=self._hwnd,
                params={"axis": str(axis), "value": float(value)},
            ),
        )

    def gamepad_state(self, *, axes: dict[str, float] | None = None, buttons: dict[str, bool] | None = None) -> None:
        """Apply a full gamepad state snapshot."""
        state = GamepadState(axes=dict(axes or {}), buttons=dict(buttons or {}))
        self._gamepad.set_state(state)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="gamepad.state",
                hwnd=self._hwnd,
                params={"axes": state.axes, "buttons": state.buttons},
            ),
        )

    async def gamepad_policy_step(self, *, meta: dict[str, object] | None = None) -> GamepadState:
        """Capture a frame and apply the configured policy output as gamepad state."""
        frame = self._capture.get_frame()
        state = await self._policy.predict(frame=frame, meta=dict(meta or {}))
        self._gamepad.set_state(state)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="gamepad.policy",
                hwnd=self._hwnd,
                params={"axes": state.axes, "buttons": state.buttons, "meta": dict(meta or {})},
            ),
        )
        return state

    def click_template(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        button: str = "left",
        timeout: float = 0.0,
        region: Box | None = None,
    ) -> bool:
        """Find and click a template."""
        if timeout > 0:
            box = self.wait_template(template, threshold, timeout, region=region)
        else:
            box = self.find_template(template, threshold, region=region)

        if box is None:
            return False

        self.click_box(box, button)
        return True

    def wait_and_click(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        timeout: float = 10.0,
        button: str = "left",
    ) -> bool:
        """Wait for template then click."""
        return self.click_template(template, threshold, button, timeout)
