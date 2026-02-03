"""Policy (inference) port for gamepad control.

Inspired by NitroGen's separation of:
- environment execution (capture + input)
- policy inference (local/remote)

Cerise keeps this as a thin, optional interface so different transports (HTTP/WS/ZMQ)
can be added later without changing the operation layer call sites.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .gamepad import GamepadState

if TYPE_CHECKING:
    import numpy as np


@runtime_checkable
class GamepadPolicy(Protocol):
    """Gamepad policy protocol (local or remote)."""

    async def predict(
        self,
        *,
        frame: np.ndarray | None = None,
        meta: dict[str, Any] | None = None,
    ) -> GamepadState:
        pass


class NullGamepadPolicy:
    """No-op policy that always returns an empty GamepadState."""

    async def predict(
        self,
        *,
        frame=None,  # noqa: ANN001
        meta: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> GamepadState:
        return GamepadState()
