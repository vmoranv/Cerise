import asyncio

import pytest
from apps.core.ai.memory import InMemoryStore, MemoryPipeline, MemoryRecord, RuleBasedMemoryExtractor
from apps.core.contracts.events import (
    MEMORY_CORE_UPDATED,
    MEMORY_FACT_UPSERTED,
    MEMORY_HABIT_RECORDED,
    MEMORY_RECORDED,
    build_memory_recorded,
)
from apps.core.infrastructure import Event, MessageBus


@pytest.mark.asyncio
async def test_rule_based_extractor_metadata() -> None:
    extractor = RuleBasedMemoryExtractor()
    record = MemoryRecord(
        session_id="session-1",
        role="user",
        content="hello",
        metadata={
            "core_updates": [{"summary": "Persona: helpful", "profile_id": "profile-1"}],
            "facts": [{"subject": "User", "predicate": "likes", "object": "tea"}],
            "habits": [{"task_type": "coding", "instruction": "use type hints"}],
        },
    )

    extraction = await extractor.extract(record=record)
    assert len(extraction.core_updates) == 1
    assert extraction.core_updates[0].profile_id == "profile-1"
    assert len(extraction.facts) == 1
    assert extraction.facts[0].object == "tea"
    assert len(extraction.habits) == 1
    assert extraction.habits[0].task_type == "coding"


@pytest.mark.asyncio
async def test_memory_pipeline_emits_events() -> None:
    MessageBus.reset()
    bus = MessageBus()
    await bus.start()

    store = InMemoryStore()
    record = MemoryRecord(
        session_id="session-1",
        role="user",
        content="hello",
        metadata={
            "core_updates": [{"summary": "Persona: helpful", "profile_id": "profile-1"}],
            "facts": [{"subject": "User", "predicate": "likes", "object": "tea"}],
            "habits": [{"task_type": "coding", "instruction": "use type hints"}],
        },
    )
    await store.add(record)

    extractor = RuleBasedMemoryExtractor()
    pipeline = MemoryPipeline(bus=bus, store=store, extractor=extractor)
    pipeline.attach()

    seen: set[str] = set()
    done = asyncio.Event()

    async def capture(event: Event) -> None:
        seen.add(event.type)
        if {MEMORY_CORE_UPDATED, MEMORY_FACT_UPSERTED, MEMORY_HABIT_RECORDED}.issubset(seen):
            done.set()

    bus.subscribe(MEMORY_CORE_UPDATED, capture)
    bus.subscribe(MEMORY_FACT_UPSERTED, capture)
    bus.subscribe(MEMORY_HABIT_RECORDED, capture)

    await bus.publish(
        Event(
            type=MEMORY_RECORDED,
            data=build_memory_recorded(record.id, record.session_id),
            source="test",
        )
    )
    await asyncio.wait_for(done.wait(), timeout=2)
    await bus.wait_empty()

    await bus.stop()
    MessageBus.reset()

    assert MEMORY_CORE_UPDATED in seen
    assert MEMORY_FACT_UPSERTED in seen
    assert MEMORY_HABIT_RECORDED in seen
