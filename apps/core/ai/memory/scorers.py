"""
Memory scoring strategies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from .time_utils import ensure_timezone, now
from .types import MemoryRecord


class MemoryScorer(Protocol):
    """Scoring strategy for memory records."""

    name: str

    def score(self, query: str, record: MemoryRecord) -> float:
        """Score a record against a query."""


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z0-9']+|[\u4e00-\u9fff]", text.lower())
    return {token for token in tokens if token}


@dataclass
class KeywordOverlapScorer:
    """Simple keyword overlap scorer."""

    name: str = "keyword_overlap"

    def score(self, query: str, record: MemoryRecord) -> float:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return 0.0
        record_tokens = _tokenize(record.content)
        overlap = len(query_tokens & record_tokens)
        return overlap / max(len(query_tokens), 1)


@dataclass
class RecencyScorer:
    """Boost recent memories."""

    name: str = "recency"
    half_life: timedelta = timedelta(minutes=30)
    weight: float = 1.0

    def score(self, query: str, record: MemoryRecord) -> float:  # pylint: disable=unused-argument
        created_at = ensure_timezone(record.created_at)
        age_seconds = max((now() - created_at).total_seconds(), 0.0)
        half_life_seconds = max(self.half_life.total_seconds(), 1.0)
        decay = 0.5 ** (age_seconds / half_life_seconds)
        return decay * self.weight


@dataclass
class ImportanceScorer:
    """Boost important memories."""

    name: str = "importance"
    weight: float = 0.15

    def score(self, query: str, record: MemoryRecord) -> float:  # pylint: disable=unused-argument
        if record.importance is None:
            return 0.0
        importance = max(0.0, min(float(record.importance) / 100.0, 1.0))
        return importance * self.weight


@dataclass
class EmotionImpactScorer:
    """Boost memories with emotional signals."""

    name: str = "emotion"
    weight: float = 0.1

    def score(self, query: str, record: MemoryRecord) -> float:  # pylint: disable=unused-argument
        impact_score = 0.0
        if record.emotional_impact is not None:
            impact_score = max(0.0, min(float(record.emotional_impact) / 100.0, 1.0))
        emotion_score = _emotion_intensity(record.emotion)
        return max(impact_score, emotion_score) * self.weight


@dataclass
class ReinforcementScorer:
    """Boost frequently accessed memories."""

    name: str = "reinforcement"
    weight: float = 0.05
    max_access_count: int = 20

    def score(self, query: str, record: MemoryRecord) -> float:  # pylint: disable=unused-argument
        access_count = record.access_count or 0
        if access_count <= 0:
            return 0.0
        cap = max(self.max_access_count, 1)
        return min(float(access_count) / cap, 1.0) * self.weight


def _emotion_intensity(emotion: dict[str, float] | None) -> float:
    if not emotion:
        return 0.0
    if "intensity" in emotion:
        return max(0.0, min(float(emotion["intensity"]), 1.0))
    values = [abs(float(value)) for value in emotion.values() if isinstance(value, (int, float))]
    if not values:
        return 0.0
    avg = sum(values) / len(values)
    return max(0.0, min(avg, 1.0))
