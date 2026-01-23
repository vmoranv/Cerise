import pytest
from apps.core.ai.memory import (
    CoreProfile,
    InMemoryStore,
    MemoryConfig,
    MemoryContextBuilder,
    MemoryMaintenance,
    MemoryRecord,
    MemoryResult,
    ProceduralHabit,
    SemanticFact,
)
from apps.core.ai.memory.compression import MemoryCompressor
from apps.core.ai.memory.engine import MemoryEngine


class _CoreProvider:
    async def list_profiles(self, session_id=None):
        return [
            CoreProfile(
                profile_id="profile-1",
                summary="helpful persona",
                session_id=session_id,
                updated_at=MemoryRecord(session_id="s", role="system", content="").created_at,
            )
        ]


class _FactsProvider:
    async def list_facts(self, *, session_id=None, subject=None):
        return [
            SemanticFact(
                fact_id="fact-1",
                session_id=session_id or "session-1",
                subject="User",
                predicate="likes",
                object="tea",
                updated_at=MemoryRecord(session_id="s", role="system", content="").created_at,
            )
        ]


class _HabitsProvider:
    async def list_habits(self, *, session_id=None, task_type=None):
        return [
            ProceduralHabit(
                habit_id="habit-1",
                session_id=session_id or "session-1",
                task_type="coding",
                instruction="use type hints",
                updated_at=MemoryRecord(session_id="s", role="system", content="").created_at,
            )
        ]


@pytest.mark.asyncio
async def test_context_builder_includes_layers() -> None:
    config = MemoryConfig().context
    builder = MemoryContextBuilder(
        config=config,
        core_profiles=_CoreProvider(),
        facts=_FactsProvider(),
        habits=_HabitsProvider(),
    )
    record = MemoryRecord(session_id="session-1", role="user", content="hello world")
    results = [MemoryResult(record=record, score=0.8)]

    context = await builder.build(results, session_id="session-1")
    assert "[Core Profile]" in context
    assert "[Facts]" in context
    assert "[Habits]" in context
    assert "[Episodic Recall]" in context


@pytest.mark.asyncio
async def test_recall_updates_access_count() -> None:
    store = InMemoryStore()
    config = MemoryConfig()
    engine = MemoryEngine(store=store, config=config)

    record = MemoryRecord(session_id="session-1", role="user", content="hello world")
    await store.add(record)

    results = await engine.recall("hello", limit=1, session_id="session-1")
    assert results

    updated = await store.get(record.id)
    assert updated is not None
    assert updated.access_count == 1
    assert updated.last_accessed is not None


@pytest.mark.asyncio
async def test_random_recall_trigger() -> None:
    store = InMemoryStore()
    config = MemoryConfig()
    config.vector.enabled = False
    config.sparse.enabled = False
    config.recall.random_enabled = True
    config.recall.random_probability = 0.0
    config.recall.random_k = 1
    config.recall.trigger_keywords = ["random"]

    engine = MemoryEngine(store=store, config=config)
    record = MemoryRecord(session_id="session-1", role="user", content="unrelated")
    await store.add(record)

    results = await engine.recall("random", limit=1, session_id="session-1")
    assert results
    assert results[0].record.id == record.id


@pytest.mark.asyncio
async def test_emotion_filtering() -> None:
    store = InMemoryStore()
    config = MemoryConfig()
    config.scoring.emotion_filter_enabled = True
    config.scoring.emotion_min_intensity = 0.5

    engine = MemoryEngine(store=store, config=config)

    high = MemoryRecord(
        session_id="session-1",
        role="user",
        content="hello there",
        metadata={"emotion": {"intensity": 0.9}},
    )
    low = MemoryRecord(
        session_id="session-1",
        role="user",
        content="hello there",
        metadata={"emotion": {"intensity": 0.1}},
    )
    await store.add(high)
    await store.add(low)

    results = await engine.recall("hello", limit=2, session_id="session-1")
    assert any(item.record.id == high.id for item in results)
    assert all(item.record.id != low.id for item in results)


@pytest.mark.asyncio
async def test_memory_maintenance_prunes_low_score() -> None:
    store = InMemoryStore()
    config = MemoryConfig()
    config.dreaming.enabled = True
    config.dreaming.prune_score_threshold = 0.4
    config.dreaming.min_importance = 0.2

    record = MemoryRecord(session_id="session-1", role="user", content="old")
    record.importance = 0
    await store.add(record)

    maintenance = MemoryMaintenance(store=store, config=config)
    result = await maintenance.run(session_id="session-1")
    assert result["deleted"] == 1


@pytest.mark.asyncio
async def test_memory_compressor_async_fallback() -> None:
    compressor = MemoryCompressor(threshold=1, window=1, max_chars=200)
    record = MemoryRecord(session_id="session-1", role="user", content="hello world")
    summary = await compressor.compress_async([record])
    assert summary.metadata.get("summary") is True
    assert summary.metadata.get("compressed") is True
