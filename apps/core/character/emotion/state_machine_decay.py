"""
Emotion decay helpers.
"""

import asyncio

from .types import EmotionState, EmotionStateData


class DecayMixin:
    _current: EmotionStateData
    _decay_task: asyncio.Task | None
    DECAY_RATES: dict[EmotionState, float]

    async def start_decay(self) -> None:
        """Start emotion decay towards neutral."""
        if self._decay_task:
            return
        self._decay_task = asyncio.create_task(self._decay_loop())

    async def stop_decay(self) -> None:
        """Stop emotion decay."""
        if self._decay_task:
            self._decay_task.cancel()
            self._decay_task = None

    async def _decay_loop(self) -> None:
        """Gradually decay emotion intensity."""
        while True:
            await asyncio.sleep(1.0)

            if self._current.state == EmotionState.NEUTRAL:
                continue

            decay_rate = self.DECAY_RATES.get(self._current.state, 0.05)
            self._current.intensity -= decay_rate

            if self._current.intensity <= 0:
                await self.transition_to(EmotionState.NEUTRAL, duration=1.0)
