"""
Registry for memory scoring plugins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from .config import MemoryConfig
from .scorers import (
    EmotionImpactScorer,
    ImportanceScorer,
    KeywordOverlapScorer,
    MemoryScorer,
    RecencyScorer,
    ReinforcementScorer,
)


@dataclass
class MemoryScorerRegistry:
    """Registry for memory scorers with priority ordering."""

    _scorers: list[tuple[int, MemoryScorer]] = field(default_factory=list)

    def register(self, scorer: MemoryScorer, priority: int = 100) -> None:
        self._scorers.append((priority, scorer))
        self._scorers.sort(key=lambda item: item[0])

    def build(self) -> list[MemoryScorer]:
        return [scorer for _, scorer in self._scorers]

    @classmethod
    def default(cls, config: MemoryConfig | None = None) -> MemoryScorerRegistry:
        registry = cls()
        registry.register(KeywordOverlapScorer(), priority=10)

        scoring = config.scoring if config else None
        half_life_seconds = scoring.recency_half_life_seconds if scoring else 1800
        recency_weight = scoring.recency_weight if scoring else 1.0
        registry.register(
            RecencyScorer(half_life=timedelta(seconds=half_life_seconds), weight=recency_weight),
            priority=20,
        )

        if scoring:
            registry.register(ImportanceScorer(weight=scoring.importance_weight), priority=30)
            registry.register(EmotionImpactScorer(weight=scoring.emotional_weight), priority=40)
            registry.register(
                ReinforcementScorer(weight=scoring.reinforcement_weight, max_access_count=scoring.max_access_count),
                priority=50,
            )
        return registry
