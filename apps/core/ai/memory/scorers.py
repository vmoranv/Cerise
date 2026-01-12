"""
Memory scoring strategies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

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

    def score(self, query: str, record: MemoryRecord) -> float:  # pylint: disable=unused-argument
        age_seconds = max((datetime.utcnow() - record.created_at).total_seconds(), 0.0)
        half_life_seconds = max(self.half_life.total_seconds(), 1.0)
        decay = 0.5 ** (age_seconds / half_life_seconds)
        return decay
