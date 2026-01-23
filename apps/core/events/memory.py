"""
Event handlers for memory ingestion.
"""

from __future__ import annotations

from ..contracts.events import (
    DIALOGUE_ASSISTANT_RESPONSE,
    DIALOGUE_USER_MESSAGE,
    MEMORY_CORE_UPDATED,
    MEMORY_FACT_UPSERTED,
    MEMORY_HABIT_RECORDED,
)
from ..infrastructure import Event, EventBus
from ..services.ports import (
    CoreProfileService,
    EmotionService,
    MemoryService,
    ProceduralHabitsService,
    SemanticFactsService,
)


class MemoryEventHandler:
    """Attach dialogue events to memory ingestion."""

    def __init__(
        self,
        bus: EventBus,
        memory: MemoryService,
        emotion: EmotionService | None = None,
        *,
        enable_emotion_snapshot: bool = True,
    ):
        self._bus = bus
        self._memory = memory
        self._emotion = emotion
        self._emotion_enabled = enable_emotion_snapshot

    def attach(self) -> None:
        """Subscribe to dialogue events."""
        self._bus.subscribe(DIALOGUE_USER_MESSAGE, self._handle_user_message)
        self._bus.subscribe(DIALOGUE_ASSISTANT_RESPONSE, self._handle_assistant_message)

    def _build_metadata(self, content: str, *, model: str | None = None) -> dict:
        metadata: dict = {}
        if model:
            metadata["model"] = model
        if self._emotion_enabled and self._emotion:
            result = self._emotion.analyze(content)
            metadata["emotion_primary"] = result.primary_emotion.value
            metadata["emotion"] = {
                "valence": result.valence,
                "arousal": result.arousal,
                "dominance": result.dominance,
                "intensity": result.confidence,
                "confidence": result.confidence,
            }
        return metadata

    async def _handle_user_message(self, event: Event) -> None:
        data = event.data or {}
        session_id = data.get("session_id", "")
        content = data.get("content", "")
        if not session_id or not content:
            return
        metadata = self._build_metadata(content)
        await self._memory.ingest_message(
            session_id=session_id,
            role="user",
            content=content,
            metadata=metadata or None,
        )

    async def _handle_assistant_message(self, event: Event) -> None:
        data = event.data or {}
        session_id = data.get("session_id", "")
        content = data.get("content", "")
        if not session_id or not content:
            return
        metadata = self._build_metadata(content, model=data.get("model", ""))
        await self._memory.ingest_message(
            session_id=session_id,
            role="assistant",
            content=content,
            metadata=metadata or None,
        )


class MemoryLayerEventHandler:
    """Attach memory layer update events to stores."""

    def __init__(
        self,
        bus: EventBus,
        core_profiles: CoreProfileService,
        facts: SemanticFactsService,
        habits: ProceduralHabitsService,
    ) -> None:
        self._bus = bus
        self._core_profiles = core_profiles
        self._facts = facts
        self._habits = habits
        self._attached = False

    def attach(self) -> None:
        """Subscribe to memory layer update events."""
        if self._attached:
            return
        self._bus.subscribe(MEMORY_CORE_UPDATED, self._handle_core_updated)
        self._bus.subscribe(MEMORY_FACT_UPSERTED, self._handle_fact_upserted)
        self._bus.subscribe(MEMORY_HABIT_RECORDED, self._handle_habit_recorded)
        self._attached = True

    async def _handle_core_updated(self, event: Event) -> None:
        data = event.data or {}
        profile_id = data.get("profile_id", "")
        summary = data.get("summary", "")
        if not profile_id or not summary:
            return
        await self._core_profiles.upsert_profile(
            profile_id=profile_id,
            summary=summary,
            session_id=data.get("session_id"),
        )

    async def _handle_fact_upserted(self, event: Event) -> None:
        data = event.data or {}
        fact_id = data.get("fact_id", "")
        session_id = data.get("session_id", "")
        subject = data.get("subject", "")
        predicate = data.get("predicate", "")
        object_value = data.get("object", "")
        if not (fact_id and session_id and subject and predicate and object_value):
            return
        await self._facts.upsert_fact(
            fact_id=fact_id,
            session_id=session_id,
            subject=subject,
            predicate=predicate,
            object=object_value,
        )

    async def _handle_habit_recorded(self, event: Event) -> None:
        data = event.data or {}
        habit_id = data.get("habit_id", "")
        session_id = data.get("session_id", "")
        task_type = data.get("task_type", "")
        instruction = data.get("instruction", "")
        if not (habit_id and session_id and task_type and instruction):
            return
        await self._habits.record_habit(
            habit_id=habit_id,
            session_id=session_id,
            task_type=task_type,
            instruction=instruction,
        )
