"""Gamepad input abstraction.

This module intentionally keeps the interface minimal so that different backends
(e.g. vgamepad, DirectInput, remote policy servers) can be plugged in later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class GamepadState:
    """Normalized gamepad state snapshot."""

    axes: dict[str, float] = field(default_factory=dict)
    buttons: dict[str, bool] = field(default_factory=dict)


@runtime_checkable
class Gamepad(Protocol):
    """Gamepad backend protocol."""

    def connect(self) -> bool: ...

    def connected(self) -> bool: ...

    def set_button(self, button: str, pressed: bool) -> None: ...

    def set_axis(self, axis: str, value: float) -> None: ...

    def set_state(self, state: GamepadState) -> None: ...

    def close(self) -> None: ...


class NullGamepad:
    """No-op gamepad backend for environments without gamepad support."""

    def __init__(self) -> None:
        self._connected = False
        self._state = GamepadState()

    def connect(self) -> bool:
        self._connected = True
        return True

    def connected(self) -> bool:
        return self._connected

    def set_button(self, button: str, pressed: bool) -> None:
        self._state.buttons[str(button)] = bool(pressed)

    def set_axis(self, axis: str, value: float) -> None:
        self._state.axes[str(axis)] = float(value)

    def set_state(self, state: GamepadState) -> None:
        self._state = state

    def close(self) -> None:
        self._connected = False
