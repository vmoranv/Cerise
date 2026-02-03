"""Callable-based policy implementation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import numpy as np

from .gamepad import GamepadState

PredictCallable = Callable[[np.ndarray | None, dict[str, Any]], Awaitable[GamepadState]]


class CallableGamepadPolicy:
    """Policy wrapper around an async callable."""

    def __init__(self, predict: PredictCallable) -> None:
        self._predict = predict

    async def predict(self, *, frame: np.ndarray | None = None, meta: dict[str, Any] | None = None) -> GamepadState:
        return await self._predict(frame, dict(meta or {}))
