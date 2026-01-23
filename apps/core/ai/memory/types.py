"""
Memory types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .time_utils import ensure_timezone, from_timestamp, now


class MemoryLayer(StrEnum):
    """Memory layers for storage and recall."""

    CORE = "core"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"


class MemoryType(StrEnum):
    """Memory types aligned to retention horizons."""

    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    MUSCLE = "muscle"


def _coerce_layer(value: MemoryLayer | str | None) -> MemoryLayer | None:
    if value is None:
        return None
    if isinstance(value, MemoryLayer):
        return value
    try:
        return MemoryLayer(value)
    except ValueError:
        return None


def _coerce_memory_type(value: MemoryType | str | None) -> MemoryType | None:
    if value is None:
        return None
    if isinstance(value, MemoryType):
        return value
    try:
        return MemoryType(value)
    except ValueError:
        return None


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_timezone(value)
    if isinstance(value, (int, float)):
        return from_timestamp(float(value))
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return ensure_timezone(parsed)
    return None


@dataclass
class MemoryRecord:
    """Single memory record."""

    session_id: str
    role: str
    content: str
    layer: MemoryLayer | None = None
    memory_type: MemoryType | None = None
    category: str | None = None
    tags: list[str] | None = None
    importance: int | None = None
    emotional_impact: int | None = None
    last_accessed: datetime | None = None
    access_count: int | None = None
    emotion: dict[str, float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=now)
    id: str = field(default_factory=lambda: str(uuid4()))

    def touch(self, accessed_at: datetime | None = None) -> None:
        """Update access metadata for reinforcement."""
        current_time = ensure_timezone(accessed_at) if accessed_at else now()
        self.last_accessed = current_time
        self.access_count = (self.access_count or 0) + 1
        self.metadata["last_accessed"] = current_time.isoformat()
        self.metadata["access_count"] = self.access_count

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, dict):
            self.metadata = {}

        self.layer = _coerce_layer(self.layer) or _coerce_layer(self.metadata.get("layer"))
        if self.layer:
            self.metadata["layer"] = self.layer.value

        self.memory_type = _coerce_memory_type(self.memory_type) or _coerce_memory_type(
            self.metadata.get("memory_type")
        )
        if self.memory_type:
            self.metadata["memory_type"] = self.memory_type.value

        if self.category is None and isinstance(self.metadata.get("category"), str):
            self.category = self.metadata["category"]
        if self.category is not None:
            self.metadata["category"] = self.category

        if self.tags is None:
            meta_tags = self.metadata.get("tags")
            if isinstance(meta_tags, list):
                self.tags = [str(tag) for tag in meta_tags]
        if self.tags is not None:
            self.metadata["tags"] = list(self.tags)

        self.importance = _coerce_int(self.importance)
        if self.importance is None:
            self.importance = _coerce_int(self.metadata.get("importance"))
        if self.importance is not None:
            self.metadata["importance"] = self.importance

        self.emotional_impact = _coerce_int(self.emotional_impact)
        if self.emotional_impact is None:
            self.emotional_impact = _coerce_int(self.metadata.get("emotional_impact"))
        if self.emotional_impact is not None:
            self.metadata["emotional_impact"] = self.emotional_impact

        self.last_accessed = _coerce_datetime(self.last_accessed) or _coerce_datetime(
            self.metadata.get("last_accessed")
        )
        if self.last_accessed is not None:
            self.metadata["last_accessed"] = self.last_accessed.isoformat()

        self.access_count = _coerce_int(self.access_count)
        if self.access_count is None:
            self.access_count = _coerce_int(self.metadata.get("access_count"))
        if self.access_count is not None:
            self.metadata["access_count"] = self.access_count

        if self.emotion is None:
            stored_emotion = self.metadata.get("emotion")
            if isinstance(stored_emotion, dict):
                self.emotion = stored_emotion
        if self.emotion is not None:
            self.metadata["emotion"] = self.emotion


@dataclass
class MemoryResult:
    """Memory recall result with score."""

    record: MemoryRecord
    score: float


@dataclass(slots=True)
class CoreProfile:
    """Core profile snapshot."""

    profile_id: str
    summary: str
    session_id: str | None
    updated_at: datetime


@dataclass(slots=True)
class SemanticFact:
    """Semantic fact record."""

    fact_id: str
    session_id: str
    subject: str
    predicate: str
    object: str
    updated_at: datetime


@dataclass(slots=True)
class ProceduralHabit:
    """Procedural habit record."""

    habit_id: str
    session_id: str
    task_type: str
    instruction: str
    updated_at: datetime
