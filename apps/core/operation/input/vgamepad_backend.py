"""Optional vgamepad backend.

Requires the third-party `vgamepad` package, which is intentionally not a core
dependency.
"""

from __future__ import annotations

from .gamepad import GamepadState


class VGamepadGamepad:
    """Virtual Xbox 360 gamepad backend (requires `vgamepad`)."""

    def __init__(self) -> None:
        try:
            import vgamepad as vg
        except ImportError as e:  # pragma: no cover
            raise ImportError("vgamepad not installed. Install with: pip install vgamepad") from e

        self._vg = vg.VX360Gamepad()
        self._connected = False
        self._lx = 0.0
        self._ly = 0.0
        self._rx = 0.0
        self._ry = 0.0

    def connect(self) -> bool:
        self._connected = True
        return True

    def connected(self) -> bool:
        return self._connected

    def set_button(self, button: str, pressed: bool) -> None:
        if not self._connected:
            return
        name = str(button).lower()
        pressed = bool(pressed)

        mapping = {
            "a": self._vg.press_button if pressed else self._vg.release_button,
            "b": self._vg.press_button if pressed else self._vg.release_button,
            "x": self._vg.press_button if pressed else self._vg.release_button,
            "y": self._vg.press_button if pressed else self._vg.release_button,
        }
        if name not in mapping:
            return

        from vgamepad import XUSB_BUTTON

        btn = {
            "a": XUSB_BUTTON.XUSB_GAMEPAD_A,
            "b": XUSB_BUTTON.XUSB_GAMEPAD_B,
            "x": XUSB_BUTTON.XUSB_GAMEPAD_X,
            "y": XUSB_BUTTON.XUSB_GAMEPAD_Y,
        }[name]
        mapping[name](btn)
        self._vg.update()

    def set_axis(self, axis: str, value: float) -> None:
        if not self._connected:
            return
        name = str(axis).lower()
        value = float(value)
        value = max(-1.0, min(1.0, value))

        if name in {"lx", "left_x"}:
            self._lx = value
            self._vg.left_joystick_float(x_value_float=self._lx, y_value_float=self._ly)
        elif name in {"ly", "left_y"}:
            self._ly = value
            self._vg.left_joystick_float(x_value_float=self._lx, y_value_float=self._ly)
        elif name in {"rx", "right_x"}:
            self._rx = value
            self._vg.right_joystick_float(x_value_float=self._rx, y_value_float=self._ry)
        elif name in {"ry", "right_y"}:
            self._ry = value
            self._vg.right_joystick_float(x_value_float=self._rx, y_value_float=self._ry)
        else:
            return
        self._vg.update()

    def set_state(self, state: GamepadState) -> None:
        for button, pressed in state.buttons.items():
            self.set_button(button, pressed)
        for axis, value in state.axes.items():
            self.set_axis(axis, value)

    def close(self) -> None:
        self._connected = False
