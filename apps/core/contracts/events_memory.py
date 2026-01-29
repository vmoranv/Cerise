"""Memory event contracts."""

from __future__ import annotations

from typing import TypedDict

MEMORY_RECORDED = "memory.recorded"
MEMORY_CORE_UPDATED = "memory.core.updated"
MEMORY_FACT_UPSERTED = "memory.fact.upserted"
MEMORY_HABIT_RECORDED = "memory.habit.recorded"
MEMORY_EMOTIONAL_SNAPSHOT_ATTACHED = "memory.emotional_snapshot.attached"


class MemoryRecordedPayload(TypedDict):
    record_id: str
    session_id: str


def build_memory_recorded(record_id: str, session_id: str) -> MemoryRecordedPayload:
    return {"record_id": record_id, "session_id": session_id}


class MemoryCoreUpdatedPayload(TypedDict):
    profile_id: str
    summary: str
    session_id: str | None


def build_memory_core_updated(
    profile_id: str,
    summary: str,
    session_id: str | None = None,
) -> MemoryCoreUpdatedPayload:
    return {"profile_id": profile_id, "summary": summary, "session_id": session_id}


class MemoryFactUpsertedPayload(TypedDict):
    fact_id: str
    session_id: str
    subject: str
    predicate: str
    object: str


def build_memory_fact_upserted(
    fact_id: str,
    session_id: str,
    subject: str,
    predicate: str,
    object: str,
) -> MemoryFactUpsertedPayload:
    return {
        "fact_id": fact_id,
        "session_id": session_id,
        "subject": subject,
        "predicate": predicate,
        "object": object,
    }


class MemoryHabitRecordedPayload(TypedDict):
    habit_id: str
    session_id: str
    task_type: str
    instruction: str


def build_memory_habit_recorded(
    habit_id: str,
    session_id: str,
    task_type: str,
    instruction: str,
) -> MemoryHabitRecordedPayload:
    return {
        "habit_id": habit_id,
        "session_id": session_id,
        "task_type": task_type,
        "instruction": instruction,
    }


class MemoryEmotionalSnapshotAttachedPayload(TypedDict):
    record_id: str
    session_id: str
    emotion: dict[str, float]


def build_memory_emotional_snapshot_attached(
    record_id: str,
    session_id: str,
    emotion: dict[str, float],
) -> MemoryEmotionalSnapshotAttachedPayload:
    return {"record_id": record_id, "session_id": session_id, "emotion": emotion}


__all__ = [
    "MEMORY_RECORDED",
    "MEMORY_CORE_UPDATED",
    "MEMORY_FACT_UPSERTED",
    "MEMORY_HABIT_RECORDED",
    "MEMORY_EMOTIONAL_SNAPSHOT_ATTACHED",
    "MemoryRecordedPayload",
    "MemoryCoreUpdatedPayload",
    "MemoryFactUpsertedPayload",
    "MemoryHabitRecordedPayload",
    "MemoryEmotionalSnapshotAttachedPayload",
    "build_memory_recorded",
    "build_memory_core_updated",
    "build_memory_fact_upserted",
    "build_memory_habit_recorded",
    "build_memory_emotional_snapshot_attached",
]
