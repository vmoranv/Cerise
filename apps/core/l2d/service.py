"""
Live2D driver integration via plugin abilities.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Protocol

from ..abilities import AbilityContext, AbilityRegistry, AbilityResult
from ..infrastructure import Event, MessageBus

logger = logging.getLogger(__name__)


class AbilityRegistryProtocol(Protocol):
    """Minimal ability registry interface."""

    def get(self, name: str):
        """Return an ability instance or None."""

    async def execute(
        self,
        ability_name: str,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        """Execute an ability by name."""


@dataclass
class Live2DService:
    """Push emotion parameters to Live2D via plugin abilities."""

    bus: MessageBus
    ability_registry: AbilityRegistryProtocol = AbilityRegistry
    emotion_ability: str = "l2d.set_emotion"
    parameters_ability: str = "l2d.set_parameters"
    auto_sync: bool = True
    smoothing: float | None = None
    min_interval: float = 0.25
    _last_emit: float = field(default=0.0, init=False)
    _attached: bool = field(default=False, init=False)

    def attach(self) -> None:
        """Subscribe to emotion events."""
        if self._attached:
            return
        self.bus.subscribe("emotion.analysis.completed", self._handle_emotion_event)
        self._attached = True

    async def set_emotion(
        self,
        *,
        valence: float,
        arousal: float,
        intensity: float,
        smoothing: float | None = None,
        user_id: str = "system",
        session_id: str = "emotion",
    ) -> AbilityResult | None:
        params: dict = {
            "valence": _clamp(valence, -1.0, 1.0),
            "arousal": _clamp(arousal, 0.0, 1.0),
            "intensity": _clamp(intensity, 0.0, 1.0),
        }
        if smoothing is not None:
            params["smoothing"] = smoothing
        return await self._execute(self.emotion_ability, params, user_id, session_id)

    async def set_parameters(
        self,
        *,
        parameters: list[dict],
        smoothing: float | None = None,
        user_id: str = "system",
        session_id: str = "manual",
    ) -> AbilityResult | None:
        params: dict = {"parameters": parameters}
        if smoothing is not None:
            params["smoothing"] = smoothing
        return await self._execute(self.parameters_ability, params, user_id, session_id)

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

        result = await self.set_emotion(
            valence=valence,
            arousal=arousal,
            intensity=intensity,
            smoothing=self.smoothing,
        )
        if result and result.success:
            self._last_emit = now

    async def _execute(
        self,
        ability_name: str,
        params: dict,
        user_id: str,
        session_id: str,
    ) -> AbilityResult | None:
        if not self.ability_registry.get(ability_name):
            logger.debug("Live2D ability unavailable: %s", ability_name)
            return None

        context = AbilityContext(
            user_id=user_id,
            session_id=session_id,
            permissions=["system.execute", "network.websocket"],
        )
        result = await self.ability_registry.execute(ability_name, params, context)
        if not result.success:
            logger.warning("Live2D ability failed: %s", result.error or "unknown error")
        return result


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))
