"""
Live2D driver integration via plugin abilities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from ..abilities import AbilityContext, AbilityRegistry, AbilityResult

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

    ability_registry: AbilityRegistryProtocol = AbilityRegistry
    emotion_ability: str = "l2d.set_emotion"
    parameters_ability: str = "l2d.set_parameters"

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


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))
