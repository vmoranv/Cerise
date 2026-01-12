"""
Registry for memory scoring plugins.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .scorers import KeywordOverlapScorer, MemoryScorer, RecencyScorer


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
    def default(cls) -> MemoryScorerRegistry:
        registry = cls()
        registry.register(KeywordOverlapScorer(), priority=10)
        registry.register(RecencyScorer(), priority=20)
        return registry
