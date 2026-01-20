"""
Memory types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class MemoryLayer(StrEnum):
    """Memory layers for storage and recall."""

    CORE = "core"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"


def _coerce_layer(value: MemoryLayer | str | None) -> MemoryLayer | None:
    if value is None:
        return None
    if isinstance(value, MemoryLayer):
        return value
    try:
        return MemoryLayer(value)
    except ValueError:
        return None


@dataclass
class MemoryRecord:
    """Single memory record."""

    session_id: str
    role: str
    content: str
    layer: MemoryLayer | None = None
    emotion: dict[str, float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if not self.metadata:
            self.metadata = {}

        self.layer = _coerce_layer(self.layer) or _coerce_layer(self.metadata.get("layer"))
        if self.layer:
            self.metadata["layer"] = self.layer.value

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
