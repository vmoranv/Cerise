"""
Service ports that define seams for future service extraction.
"""

from __future__ import annotations

from typing import Protocol

from ..abilities import AbilityResult
from ..ai.emotion.types import EmotionResult
from ..ai.memory import MemoryRecord, MemoryResult


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
