import pytest
from apps.core.ai.memory.core_profile_store import CoreProfileStore
from apps.core.ai.memory.procedural_habits_store import ProceduralHabitsStore
from apps.core.ai.memory.semantic_facts_store import SemanticFactsStore


@pytest.mark.asyncio
async def test_core_profile_store_upsert_and_list() -> None:
    store = CoreProfileStore(":memory:", max_records=2)
    await store.upsert_profile(profile_id="profile-1", summary="alpha", session_id="session-1")
    await store.upsert_profile(profile_id="profile-2", summary="beta", session_id="session-2")

    profiles = await store.list_profiles()
    assert {profile.profile_id for profile in profiles} == {"profile-1", "profile-2"}

    await store.upsert_profile(profile_id="profile-1", summary="updated", session_id="session-1")
    updated = await store.get_profile("profile-1")
    assert updated is not None
    assert updated.summary == "updated"


@pytest.mark.asyncio
async def test_core_profile_store_trims_records() -> None:
    store = CoreProfileStore(":memory:", max_records=1)
    await store.upsert_profile(profile_id="profile-1", summary="alpha", session_id=None)
    await store.upsert_profile(profile_id="profile-2", summary="beta", session_id=None)

    profiles = await store.list_profiles()
    assert len(profiles) == 1
    assert profiles[0].profile_id == "profile-2"


@pytest.mark.asyncio
async def test_semantic_facts_store_upsert_conflict() -> None:
    store = SemanticFactsStore(":memory:")
    first = await store.upsert_fact(
        fact_id="fact-1",
        session_id="session-1",
        subject="User",
        predicate="likes",
        object="tea",
    )
    second = await store.upsert_fact(
        fact_id="fact-2",
        session_id="session-1",
        subject="User",
        predicate="likes",
        object="coffee",
    )

    facts = await store.list_facts(session_id="session-1")
    assert len(facts) == 1
    assert facts[0].fact_id == first.fact_id
    assert facts[0].object == "coffee"
    assert second.session_id == "session-1"


@pytest.mark.asyncio
async def test_procedural_habits_store_upsert_conflict() -> None:
    store = ProceduralHabitsStore(":memory:")
    first = await store.record_habit(
        habit_id="habit-1",
        session_id="session-1",
        task_type="coding",
        instruction="use type hints",
    )
    second = await store.record_habit(
        habit_id="habit-2",
        session_id="session-1",
        task_type="coding",
        instruction="use type hints",
    )

    habits = await store.list_habits(session_id="session-1")
    assert len(habits) == 1
    assert habits[0].habit_id == first.habit_id
    assert habits[0].instruction == "use type hints"
    assert second.session_id == "session-1"
