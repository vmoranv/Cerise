"""Memory extraction pipeline."""

from __future__ import annotations

from uuid import uuid4

from ...contracts.events import (
    MEMORY_CORE_UPDATED,
    MEMORY_EMOTIONAL_SNAPSHOT_ATTACHED,
    MEMORY_FACT_UPSERTED,
    MEMORY_HABIT_RECORDED,
    MEMORY_RECORDED,
    build_memory_core_updated,
    build_memory_emotional_snapshot_attached,
    build_memory_fact_upserted,
    build_memory_habit_recorded,
)
from ...infrastructure import Event, EventBus
from .extraction import MemoryExtraction, MemoryExtractor
from .store import MemoryStore


class MemoryPipeline:
    """Emit memory layer events from extracted updates."""

    def __init__(
        self,
        *,
        bus: EventBus,
        store: MemoryStore,
        extractor: MemoryExtractor | None = None,
    ) -> None:
        self._bus = bus
        self._store = store
        self._extractor = extractor
        self._attached = False

    def attach(self) -> None:
        """Subscribe to memory events."""
        if self._attached:
            return
        self._bus.subscribe(MEMORY_RECORDED, self._handle_recorded)
        self._attached = True

    async def _handle_recorded(self, event: Event) -> None:
        if not self._extractor:
            return
        data = event.data or {}
        record_id = data.get("record_id")
        if not record_id:
            return
        record = await self._store.get(record_id)
        if not record:
            return
        extraction = await self._extractor.extract(record=record)
        await self.emit_extraction(extraction, session_id=record.session_id)
        if record.emotion:
            self._bus.publish_sync(
                Event(
                    type=MEMORY_EMOTIONAL_SNAPSHOT_ATTACHED,
                    data=build_memory_emotional_snapshot_attached(
                        record_id=record.id,
                        session_id=record.session_id,
                        emotion=record.emotion,
                    ),
                    source="memory_pipeline",
                )
            )

    async def emit_extraction(self, extraction: MemoryExtraction, *, session_id: str | None = None) -> None:
        """Emit memory layer events for extracted updates."""
        for update in extraction.core_updates:
            profile_id = update.profile_id or f"profile-{uuid4()}"
            self._bus.publish_sync(
                Event(
                    type=MEMORY_CORE_UPDATED,
                    data=build_memory_core_updated(
                        profile_id=profile_id,
                        summary=update.summary,
                        session_id=update.session_id or session_id,
                    ),
                    source="memory_pipeline",
                )
            )

        for fact in extraction.facts:
            resolved_session = fact.session_id or session_id
            if not resolved_session:
                continue
            fact_id = fact.fact_id or f"fact-{uuid4()}"
            self._bus.publish_sync(
                Event(
                    type=MEMORY_FACT_UPSERTED,
                    data=build_memory_fact_upserted(
                        fact_id=fact_id,
                        session_id=resolved_session,
                        subject=fact.subject,
                        predicate=fact.predicate,
                        object=fact.object,
                    ),
                    source="memory_pipeline",
                )
            )

        for habit in extraction.habits:
            resolved_session = habit.session_id or session_id
            if not resolved_session:
                continue
            habit_id = habit.habit_id or f"habit-{uuid4()}"
            self._bus.publish_sync(
                Event(
                    type=MEMORY_HABIT_RECORDED,
                    data=build_memory_habit_recorded(
                        habit_id=habit_id,
                        session_id=resolved_session,
                        task_type=habit.task_type,
                        instruction=habit.instruction,
                    ),
                    source="memory_pipeline",
                )
            )
