"""
Event handlers for Live2D synchronization.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..contracts.events import EMOTION_ANALYSIS_COMPLETED
from ..infrastructure import Event, EventBus
from ..services.ports import Live2DDriver


@dataclass
class Live2DEmotionHandler:
    """Push emotion analysis events to Live2D."""

    bus: EventBus
    live2d: Live2DDriver
    auto_sync: bool = True
    smoothing: float | None = None
    min_interval: float = 0.25
    _last_emit: float = field(default=0.0, init=False)
    _attached: bool = field(default=False, init=False)

    def attach(self) -> None:
        """Subscribe to emotion events."""
        if self._attached:
            return
        self.bus.subscribe(EMOTION_ANALYSIS_COMPLETED, self._handle_emotion_event)
        self._attached = True

    async def _handle_emotion_event(self, event: Event) -> None:
        if not self.auto_sync:
            return

        now = time.monotonic()
        if now - self._last_emit < self.min_interval:
            return

        data = event.data or {}
        valence = _to_float(data.get("valence"))
        arousal = _to_float(data.get("arousal"))
        intensity = _to_float(data.get("intensity", data.get("confidence")))
        if valence is None or arousal is None or intensity is None:
            return

        result = await self.live2d.set_emotion(
            valence=valence,
            arousal=arousal,
            intensity=intensity,
            smoothing=self.smoothing,
        )
        if result and result.success:
            self._last_emit = now


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
