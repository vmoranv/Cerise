"""
Emotion state transition helpers.
"""

import asyncio
from collections.abc import Callable
from typing import Any

from ...contracts.events import CHARACTER_EMOTION_CHANGED, build_character_emotion_changed
from ...infrastructure import Event, EventBus
from .types import EmotionState, EmotionStateData


class TransitionMixin:
    _current: EmotionStateData
    _target: EmotionState | None
    _transition_progress: float
    _transition_duration: float
    _is_transitioning: bool
    _listeners: list[Callable[[EmotionState, EmotionState], None]]
    _message_bus: EventBus
    DEFAULT_TRANSITION_DURATION: float

    def set_emotion(
        self,
        emotion: EmotionState | str,
        intensity: float = 1.0,
        duration: float | None = None,
    ) -> None:
        """Set a new emotion state."""
        if isinstance(emotion, str):
            try:
                emotion = EmotionState(emotion)
            except ValueError:
                emotion = EmotionState.NEUTRAL

        if emotion == self._current.state:
            self._current.intensity = min(1.0, max(0.0, intensity))
            return

        old_state = self._current.state
        self._target = emotion
        self._transition_duration = duration or self.DEFAULT_TRANSITION_DURATION
        self._transition_progress = 0.0
        self._is_transitioning = True

        self._current = EmotionStateData(
            state=emotion,
            intensity=intensity,
        )
        self._is_transitioning = False
        self._target = None

        for listener in self._listeners:
            try:
                listener(old_state, emotion)
            except Exception:
                pass

        self._message_bus.publish_sync(
            Event(
                type=CHARACTER_EMOTION_CHANGED,
                data=dict(
                    build_character_emotion_changed(
                        from_state=old_state.value,
                        to_state=emotion.value,
                        intensity=intensity,
                    )
                ),
                source="emotion_state_machine",
            )
        )

    async def transition_to(
        self,
        emotion: EmotionState,
        duration: float = 0.5,
        intensity: float = 1.0,
    ) -> None:
        """Smoothly transition to a new emotion."""
        if emotion == self._current.state:
            self._current.intensity = intensity
            return

        old_state = self._current.state
        self._target = emotion
        self._transition_duration = duration
        self._is_transitioning = True

        steps = int(duration * 60)
        step_time = duration / steps

        for i in range(steps):
            self._transition_progress = (i + 1) / steps
            self._current.blend_weight = 1.0 - self._transition_progress
            await asyncio.sleep(step_time)

        self._current = EmotionStateData(
            state=emotion,
            intensity=intensity,
        )
        self._is_transitioning = False
        self._target = None

        for listener in self._listeners:
            try:
                listener(old_state, emotion)
            except Exception:
                pass

        payload: dict[str, Any] = dict(
            build_character_emotion_changed(
                from_state=old_state.value,
                to_state=emotion.value,
                intensity=intensity,
            )
        )
        await self._message_bus.emit(
            CHARACTER_EMOTION_CHANGED,
            payload,
            source="emotion_state_machine",
        )
