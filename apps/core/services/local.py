"""
Local adapters for service ports.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..abilities import AbilityResult
from ..ai import EmotionAnalyzer
from ..ai.emotion.types import EmotionResult
from ..ai.memory import MemoryEngine, MemoryRecord, MemoryResult
from ..ai.memory.context_builder import MemoryContextBuilder
from ..ai.memory.layer_store import (
    CoreProfileStateStore,
    CoreProfileStore,
    ProceduralHabitsStateStore,
    ProceduralHabitsStore,
    SemanticFactsStateStore,
    SemanticFactsStore,
)
from ..l2d import Live2DService
from .ports import (
    CoreProfile,
    CoreProfileService,
    EmotionService,
    Live2DDriver,
    MemoryService,
    ProceduralHabit,
    ProceduralHabitsService,
    SemanticFact,
    SemanticFactsService,
)


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

    def __init__(self, engine: MemoryEngine, *, context_builder: MemoryContextBuilder | None = None):
        self._engine = engine
        self._context_builder = context_builder

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

    async def format_context(self, results: list[MemoryResult], *, session_id: str | None = None) -> str:
        if self._context_builder:
            return await self._context_builder.build(results, session_id)
        return self._engine.format_context(results)


class LocalCoreProfileService(CoreProfileService):
    """In-process core profile adapter."""

    def __init__(
        self,
        store: CoreProfileStore | CoreProfileStateStore | None = None,
    ) -> None:
        self._store = store

    async def upsert_profile(
        self,
        *,
        profile_id: str,
        summary: str,
        session_id: str | None = None,
    ) -> CoreProfile:
        if not self._store:
            return CoreProfile(
                profile_id=profile_id,
                summary=summary,
                session_id=session_id,
                updated_at=datetime.now(UTC),
            )
        return await self._store.upsert_profile(
            profile_id=profile_id,
            summary=summary,
            session_id=session_id,
        )

    async def get_profile(self, profile_id: str) -> CoreProfile | None:
        if not self._store:
            return None
        return await self._store.get_profile(profile_id)

    async def list_profiles(self, session_id: str | None = None) -> list[CoreProfile]:
        if not self._store:
            return []
        return await self._store.list_profiles(session_id=session_id)


class LocalSemanticFactsService(SemanticFactsService):
    """In-process semantic facts adapter."""

    def __init__(
        self,
        store: SemanticFactsStore | SemanticFactsStateStore | None = None,
    ) -> None:
        self._store = store

    async def upsert_fact(
        self,
        *,
        fact_id: str,
        session_id: str,
        subject: str,
        predicate: str,
        object: str,
    ) -> SemanticFact:
        if not self._store:
            return SemanticFact(
                fact_id=fact_id,
                session_id=session_id,
                subject=subject,
                predicate=predicate,
                object=object,
                updated_at=datetime.now(UTC),
            )
        return await self._store.upsert_fact(
            fact_id=fact_id,
            session_id=session_id,
            subject=subject,
            predicate=predicate,
            object=object,
        )

    async def list_facts(
        self,
        *,
        session_id: str | None = None,
        subject: str | None = None,
    ) -> list[SemanticFact]:
        if not self._store:
            return []
        return await self._store.list_facts(session_id=session_id, subject=subject)


class LocalProceduralHabitsService(ProceduralHabitsService):
    """In-process procedural habits adapter."""

    def __init__(
        self,
        store: ProceduralHabitsStore | ProceduralHabitsStateStore | None = None,
    ) -> None:
        self._store = store

    async def record_habit(
        self,
        *,
        habit_id: str,
        session_id: str,
        task_type: str,
        instruction: str,
    ) -> ProceduralHabit:
        if not self._store:
            return ProceduralHabit(
                habit_id=habit_id,
                session_id=session_id,
                task_type=task_type,
                instruction=instruction,
                updated_at=datetime.now(UTC),
            )
        return await self._store.record_habit(
            habit_id=habit_id,
            session_id=session_id,
            task_type=task_type,
            instruction=instruction,
        )

    async def list_habits(
        self,
        *,
        session_id: str | None = None,
        task_type: str | None = None,
    ) -> list[ProceduralHabit]:
        if not self._store:
            return []
        return await self._store.list_habits(session_id=session_id, task_type=task_type)


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
