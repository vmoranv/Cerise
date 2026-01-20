"""
Local adapters for service ports.
"""

from __future__ import annotations

from ..abilities import AbilityResult
from ..ai import EmotionAnalyzer
from ..ai.emotion.types import EmotionResult
from ..ai.memory import MemoryEngine, MemoryRecord, MemoryResult
from ..l2d import Live2DService
from .ports import EmotionService, Live2DDriver, MemoryService


class LocalEmotionService(EmotionService):
    """In-process emotion service adapter."""

    def __init__(self, analyzer: EmotionAnalyzer):
        self._analyzer = analyzer

    def analyze(self, text: str, *, character: str | None = None) -> EmotionResult:
        return self._analyzer.analyze(text, character=character)

    def analyze_for_character(self, text: str, *, character: str | None = None) -> str:
        return self._analyzer.analyze_for_character(text, character=character)


class LocalMemoryService(MemoryService):
    """In-process memory service adapter."""

    def __init__(self, engine: MemoryEngine):
        self._engine = engine

    def default_recall_limit(self) -> int:
        if not self._engine.config:
            return 5
        return self._engine.config.recall.top_k

    async def ingest_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> MemoryRecord:
        return await self._engine.ingest_message(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata,
        )

    async def recall(
        self,
        query: str,
        *,
        limit: int | None = None,
        session_id: str | None = None,
    ) -> list[MemoryResult]:
        recall_limit = limit if limit is not None else self.default_recall_limit()
        return await self._engine.recall(query, limit=recall_limit, session_id=session_id)

    def format_context(self, results: list[MemoryResult]) -> str:
        return self._engine.format_context(results)


class LocalLive2DService(Live2DDriver):
    """In-process Live2D adapter."""

    def __init__(self, live2d: Live2DService):
        self._live2d = live2d

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
        return await self._live2d.set_emotion(
            valence=valence,
            arousal=arousal,
            intensity=intensity,
            smoothing=smoothing,
            user_id=user_id,
            session_id=session_id,
        )

    async def set_parameters(
        self,
        *,
        parameters: list[dict],
        smoothing: float | None = None,
        user_id: str = "system",
        session_id: str = "manual",
    ) -> AbilityResult | None:
        return await self._live2d.set_parameters(
            parameters=parameters,
            smoothing=smoothing,
            user_id=user_id,
            session_id=session_id,
        )
