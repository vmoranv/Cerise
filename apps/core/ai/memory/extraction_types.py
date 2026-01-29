"""Types for memory extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .types import MemoryRecord


@dataclass(slots=True)
class CoreProfileUpdate:
    """Core profile update extracted from a message."""

    summary: str
    profile_id: str | None = None
    session_id: str | None = None


@dataclass(slots=True)
class SemanticFactUpdate:
    """Semantic fact extracted from a message."""

    subject: str
    predicate: str
    object: str
    fact_id: str | None = None
    session_id: str | None = None


@dataclass(slots=True)
class ProceduralHabitUpdate:
    """Procedural habit extracted from a message."""

    task_type: str
    instruction: str
    habit_id: str | None = None
    session_id: str | None = None


@dataclass(slots=True)
class MemoryExtraction:
    """Collection of extracted memory updates."""

    core_updates: list[CoreProfileUpdate] = field(default_factory=list)
    facts: list[SemanticFactUpdate] = field(default_factory=list)
    habits: list[ProceduralHabitUpdate] = field(default_factory=list)


class MemoryExtractor(Protocol):
    """Extractor interface for memory pipeline."""

    async def extract(self, *, record: MemoryRecord) -> MemoryExtraction:
        """Extract structured memory updates from a record."""
