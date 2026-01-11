"""
Emotion State Machine

Manages character emotion state with smooth transitions.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ...infrastructure import Event, MessageBus


class EmotionState(Enum):
    """Character emotion states"""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    EXCITED = "excited"
    CURIOUS = "curious"
    CONFUSED = "confused"
    SHY = "shy"
    SLEEPY = "sleepy"


@dataclass
class EmotionTransition:
    """Represents an emotion transition"""

    from_state: EmotionState
    to_state: EmotionState
    duration: float  # seconds
    easing: str = "ease-in-out"


@dataclass
class EmotionStateData:
    """Current emotion state data"""

    state: EmotionState
    intensity: float = 1.0  # 0.0 to 1.0
    blend_weight: float = 1.0  # For blending during transitions
    timestamp: datetime = field(default_factory=datetime.now)


class EmotionStateMachine:
    """Manages emotion state transitions for a character"""

    # Default transition durations (seconds)
    DEFAULT_TRANSITION_DURATION = 0.5

    # Emotion decay rates (per second)
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

    def __init__(self, initial_state: EmotionState = EmotionState.NEUTRAL):
        self._current = EmotionStateData(state=initial_state)
        self._target: EmotionState | None = None
        self._transition_progress: float = 0.0
        self._transition_duration: float = 0.0
        self._is_transitioning = False
        self._listeners: list[Callable[[EmotionState, EmotionState], None]] = []
        self._message_bus = MessageBus()
        self._decay_task: asyncio.Task | None = None

    @property
    def current_state(self) -> EmotionState:
        """Get current emotion state"""
        return self._current.state

    @property
    def current_intensity(self) -> float:
        """Get current emotion intensity"""
        return self._current.intensity

    @property
    def is_transitioning(self) -> bool:
        """Check if currently transitioning"""
        return self._is_transitioning

    def set_emotion(
        self,
        emotion: EmotionState | str,
        intensity: float = 1.0,
        duration: float | None = None,
    ) -> None:
        """Set a new emotion state"""
        if isinstance(emotion, str):
            try:
                emotion = EmotionState(emotion)
            except ValueError:
                emotion = EmotionState.NEUTRAL

        if emotion == self._current.state:
            # Just update intensity
            self._current.intensity = min(1.0, max(0.0, intensity))
            return

        old_state = self._current.state
        self._target = emotion
        self._transition_duration = duration or self.DEFAULT_TRANSITION_DURATION
        self._transition_progress = 0.0
        self._is_transitioning = True

        # For now, immediately transition (smooth transition can be async)
        self._current = EmotionStateData(
            state=emotion,
            intensity=intensity,
        )
        self._is_transitioning = False
        self._target = None

        # Notify listeners
        for listener in self._listeners:
            try:
                listener(old_state, emotion)
            except Exception:
                pass

        # Emit event
        self._message_bus.publish_sync(
            Event(
                type="character.emotion_changed",
                data={
                    "from_state": old_state.value,
                    "to_state": emotion.value,
                    "intensity": intensity,
                },
                source="emotion_state_machine",
            )
        )

    async def transition_to(
        self,
        emotion: EmotionState,
        duration: float = 0.5,
        intensity: float = 1.0,
    ) -> None:
        """Smoothly transition to a new emotion"""
        if emotion == self._current.state:
            self._current.intensity = intensity
            return

        old_state = self._current.state
        self._target = emotion
        self._transition_duration = duration
        self._is_transitioning = True

        # Gradual transition
        steps = int(duration * 60)  # 60 FPS
        step_time = duration / steps

        for i in range(steps):
            self._transition_progress = (i + 1) / steps
            self._current.blend_weight = 1.0 - self._transition_progress
            await asyncio.sleep(step_time)

        # Complete transition
        self._current = EmotionStateData(
            state=emotion,
            intensity=intensity,
        )
        self._is_transitioning = False
        self._target = None

        # Notify
        for listener in self._listeners:
            try:
                listener(old_state, emotion)
            except Exception:
                pass

        await self._message_bus.emit(
            "character.emotion_changed",
            {
                "from_state": old_state.value,
                "to_state": emotion.value,
                "intensity": intensity,
            },
            source="emotion_state_machine",
        )

    def add_listener(self, callback: Callable[[EmotionState, EmotionState], None]) -> None:
        """Add a state change listener"""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[EmotionState, EmotionState], None]) -> bool:
        """Remove a state change listener"""
        if callback in self._listeners:
            self._listeners.remove(callback)
            return True
        return False

    async def start_decay(self) -> None:
        """Start emotion decay towards neutral"""
        if self._decay_task:
            return
        self._decay_task = asyncio.create_task(self._decay_loop())

    async def stop_decay(self) -> None:
        """Stop emotion decay"""
        if self._decay_task:
            self._decay_task.cancel()
            self._decay_task = None

    async def _decay_loop(self) -> None:
        """Gradually decay emotion intensity"""
        while True:
            await asyncio.sleep(1.0)

            if self._current.state == EmotionState.NEUTRAL:
                continue

            decay_rate = self.DECAY_RATES.get(self._current.state, 0.05)
            self._current.intensity -= decay_rate

            if self._current.intensity <= 0:
                await self.transition_to(EmotionState.NEUTRAL, duration=1.0)

    def get_animation_params(self) -> dict:
        """Get parameters for animation system"""
        return {
            "emotion": self._current.state.value,
            "intensity": self._current.intensity,
            "is_transitioning": self._is_transitioning,
            "transition_progress": self._transition_progress,
            "target_emotion": self._target.value if self._target else None,
        }

    def to_dict(self) -> dict:
        """Serialize state"""
        return {
            "state": self._current.state.value,
            "intensity": self._current.intensity,
            "timestamp": self._current.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionStateMachine":
        """Deserialize state"""
        machine = cls()
        if "state" in data:
            machine.set_emotion(data["state"], data.get("intensity", 1.0))
        return machine
