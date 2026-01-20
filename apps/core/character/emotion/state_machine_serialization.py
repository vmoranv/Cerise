"""
Emotion state serialization helpers.
"""

from ...infrastructure import EventBus
from .types import EmotionState, EmotionStateData


class SerializationMixin:
    _current: EmotionStateData
    _target: EmotionState | None
    _transition_progress: float
    _is_transitioning: bool

    def get_animation_params(self) -> dict:
        """Get parameters for animation system."""
        return {
            "emotion": self._current.state.value,
            "intensity": self._current.intensity,
            "is_transitioning": self._is_transitioning,
            "transition_progress": self._transition_progress,
            "target_emotion": self._target.value if self._target else None,
        }

    def to_dict(self) -> dict:
        """Serialize state."""
        return {
            "state": self._current.state.value,
            "intensity": self._current.intensity,
            "timestamp": self._current.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict, bus: EventBus) -> "SerializationMixin":
        """Deserialize state."""
        machine = cls(bus=bus)
        if "state" in data:
            machine.set_emotion(data["state"], data.get("intensity", 1.0))
        return machine
