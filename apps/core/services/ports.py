"""
Service ports that define seams for future service extraction.
"""

from __future__ import annotations

from typing import Protocol

from ..abilities import AbilityResult
from ..ai.emotion.types import EmotionResult
from ..ai.memory import CoreProfile, MemoryRecord, MemoryResult, ProceduralHabit, SemanticFact


class EmotionService(Protocol):
    """Emotion analysis service port."""

    def analyze(self, text: str, *, character: str | None = None) -> EmotionResult:
        """Analyze text and return the full emotion result."""

    def analyze_for_character(self, text: str, *, character: str | None = None) -> str:
        """Return the primary emotion name for character animation."""


class MemoryService(Protocol):
    """Memory ingestion and recall service port."""

    def default_recall_limit(self) -> int:
        """Return the default recall limit for queries."""

    async def ingest_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> MemoryRecord:
        """Ingest a single message into memory."""

    async def recall(
        self,
        query: str,
        *,
        limit: int | None = None,
        session_id: str | None = None,
    ) -> list[MemoryResult]:
        """Recall memory results for a query."""

    def format_context(self, results: list[MemoryResult]) -> str:
        """Format memory results for prompt injection."""


class CoreProfileService(Protocol):
    """Core profile store port."""

    async def upsert_profile(
        self,
        *,
        profile_id: str,
        summary: str,
        session_id: str | None = None,
    ) -> CoreProfile:
        """Create or update a core profile snapshot."""

    async def get_profile(self, profile_id: str) -> CoreProfile | None:
        """Fetch a core profile by id."""

    async def list_profiles(self, session_id: str | None = None) -> list[CoreProfile]:
        """List core profiles."""


class SemanticFactsService(Protocol):
    """Semantic facts store port."""

    async def upsert_fact(
        self,
        *,
        fact_id: str,
        session_id: str,
        subject: str,
        predicate: str,
        object: str,
    ) -> SemanticFact:
        """Create or update a semantic fact."""

    async def list_facts(
        self,
        *,
        session_id: str | None = None,
        subject: str | None = None,
    ) -> list[SemanticFact]:
        """List semantic facts."""


class ProceduralHabitsService(Protocol):
    """Procedural habits store port."""

    async def record_habit(
        self,
        *,
        habit_id: str,
        session_id: str,
        task_type: str,
        instruction: str,
    ) -> ProceduralHabit:
        """Record a procedural habit."""

    async def list_habits(
        self,
        *,
        session_id: str | None = None,
        task_type: str | None = None,
    ) -> list[ProceduralHabit]:
        """List procedural habits."""


class Live2DDriver(Protocol):
    """Live2D downstream driver port."""

    async def set_emotion(
        self,
        *,
        valence: float,
        arousal: float,
        intensity: float,
        smoothing: float | None = None,
        user_id: str = "system",
        session_id: str = "emotion",
    ) -> AbilityResult | None:
        """Push valence/arousal/intensity to Live2D."""

    async def set_parameters(
        self,
        *,
        parameters: list[dict],
        smoothing: float | None = None,
        user_id: str = "system",
        session_id: str = "manual",
    ) -> AbilityResult | None:
        """Push arbitrary Live2D parameters."""
