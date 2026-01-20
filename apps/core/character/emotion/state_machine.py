"""
Emotion State Machine

Manages character emotion state with smooth transitions.
"""

import asyncio
from collections.abc import Callable

from ...infrastructure import EventBus
from .state_machine_decay import DecayMixin
from .state_machine_serialization import SerializationMixin
from .state_machine_transitions import TransitionMixin
from .types import EmotionState, EmotionStateData


class EmotionStateMachine(TransitionMixin, DecayMixin, SerializationMixin):
    """Manages emotion state transitions for a character."""

    DEFAULT_TRANSITION_DURATION = 0.5

    DECAY_RATES: dict[EmotionState, float] = {
        EmotionState.EXCITED: 0.1,
        EmotionState.ANGRY: 0.05,
        EmotionState.SURPRISED: 0.15,
        EmotionState.HAPPY: 0.03,
        EmotionState.SAD: 0.02,
        EmotionState.CURIOUS: 0.08,
        EmotionState.CONFUSED: 0.1,
        EmotionState.SHY: 0.06,
        EmotionState.SLEEPY: 0.01,
        EmotionState.NEUTRAL: 0.0,
    }

    def __init__(self, initial_state: EmotionState = EmotionState.NEUTRAL, bus: EventBus | None = None):
        if bus is None:
            raise ValueError("bus is required for EmotionStateMachine")
        self._current = EmotionStateData(state=initial_state)
        self._target: EmotionState | None = None
        self._transition_progress: float = 0.0
        self._transition_duration: float = 0.0
        self._is_transitioning = False
        self._listeners: list[Callable[[EmotionState, EmotionState], None]] = []
        self._message_bus = bus
        self._decay_task: asyncio.Task | None = None

    @property
    def current_state(self) -> EmotionState:
        """Get current emotion state."""
        return self._current.state

    @property
    def current_intensity(self) -> float:
        """Get current emotion intensity."""
        return self._current.intensity

    @property
    def is_transitioning(self) -> bool:
        """Check if currently transitioning."""
        return self._is_transitioning

    def add_listener(self, callback: Callable[[EmotionState, EmotionState], None]) -> None:
        """Add a state change listener."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[EmotionState, EmotionState], None]) -> bool:
        """Remove a state change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)
            return True
        return False
