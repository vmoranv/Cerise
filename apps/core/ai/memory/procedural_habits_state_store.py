"""
Procedural habits state store.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ...infrastructure import StateStore
from .types import ProceduralHabit


class ProceduralHabitsStateStore:
    """StateStore-backed procedural habits store."""

    def __init__(self, path: str | Path | None, *, max_records: int = 200) -> None:
        self._store = StateStore(path)
        self._key = "procedural_habits"
        self._max_records = max_records

    async def record_habit(
        self,
        *,
        habit_id: str,
        session_id: str,
        task_type: str,
        instruction: str,
    ) -> ProceduralHabit:
        updated_at = datetime.utcnow()
        habits = await self._load()
        existing_id = self._find_existing(habits, session_id, task_type, instruction)
        resolved_id = existing_id or habit_id
        habits[resolved_id] = {
            "habit_id": resolved_id,
            "session_id": session_id,
            "task_type": task_type,
            "instruction": instruction,
            "updated_at": updated_at.timestamp(),
        }
        habits = self._trim(habits)
        await self._store.set(self._key, habits)
        return ProceduralHabit(
            habit_id=resolved_id,
            session_id=session_id,
            task_type=task_type,
            instruction=instruction,
            updated_at=updated_at,
        )

    async def list_habits(
        self,
        *,
        session_id: str | None = None,
        task_type: str | None = None,
    ) -> list[ProceduralHabit]:
        habits = await self._load()
        values = [self._entry_to_habit(entry) for entry in habits.values()]
        if session_id is not None:
            values = [habit for habit in values if habit.session_id == session_id]
        if task_type is not None:
            values = [habit for habit in values if habit.task_type == task_type]
        return sorted(values, key=lambda habit: habit.updated_at, reverse=True)

    async def _load(self) -> dict[str, dict]:
        data = await self._store.get(self._key, {})
        if not isinstance(data, dict):
            return {}
        return data

    def _find_existing(
        self,
        habits: dict[str, dict],
        session_id: str,
        task_type: str,
        instruction: str,
    ) -> str | None:
        for habit_id, entry in habits.items():
            if (
                entry.get("session_id") == session_id
                and entry.get("task_type") == task_type
                and entry.get("instruction") == instruction
            ):
                return habit_id
        return None

    def _trim(self, habits: dict[str, dict]) -> dict[str, dict]:
        if self._max_records <= 0 or len(habits) <= self._max_records:
            return habits
        ordered = sorted(
            habits.items(),
            key=lambda item: float(item[1].get("updated_at", 0.0)),
            reverse=True,
        )
        return dict(ordered[: self._max_records])

    def _entry_to_habit(self, entry: dict) -> ProceduralHabit:
        return ProceduralHabit(
            habit_id=entry.get("habit_id", ""),
            session_id=entry.get("session_id", ""),
            task_type=entry.get("task_type", ""),
            instruction=entry.get("instruction", ""),
            updated_at=datetime.fromtimestamp(float(entry.get("updated_at", 0.0))),
        )
