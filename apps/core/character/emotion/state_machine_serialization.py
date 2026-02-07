"""
Emotion state serialization helpers.
"""

from typing import Any, TypeVar, cast

from ...infrastructure import EventBus
from .types import EmotionState, EmotionStateData

SerializationMixinT = TypeVar("SerializationMixinT", bound="SerializationMixin")


class SerializationMixin:
    _current: EmotionStateData
    _target: EmotionState | None
    _transition_progress: float
    _is_transitioning: bool

    def get_animation_params(self) -> dict[str, Any]:
        """Get parameters for animation system."""
        return {
            "emotion": self._current.state.value,
            "intensity": self._current.intensity,
            "is_transitioning": self._is_transitioning,
            "transition_progress": self._transition_progress,
            "target_emotion": self._target.value if self._target else None,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize state."""
        return {
            "state": self._current.state.value,
            "intensity": self._current.intensity,
            "timestamp": self._current.timestamp.isoformat(),
        }

    def set_emotion(
        self,
        emotion: EmotionState | str,
        intensity: float = 1.0,
        duration: float | None = None,
    ) -> None:
        raise NotImplementedError

    @classmethod
    def from_dict(
        cls: type[SerializationMixinT],
        data: dict[str, Any],
        bus: EventBus,
    ) -> SerializationMixinT:
        """Deserialize state."""
        factory = cast(Any, cls)
        machine = cast(SerializationMixinT, factory(bus=bus))
        if "state" in data:
            machine.set_emotion(cast(EmotionState | str, data["state"]), float(data.get("intensity", 1.0)))
        return machine
