"""
Procedural habits stores.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .time_utils import from_timestamp, now
from .types import ProceduralHabit


class ProceduralHabitsStore:
    """SQLite store for procedural habits."""

    def __init__(self, path: str | Path, *, max_records: int = 200) -> None:
        self._path = Path(path) if path != ":memory:" else None
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._max_records = max_records
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS procedural_habits (
                habit_id TEXT PRIMARY KEY,
                session_id TEXT,
                task_type TEXT,
                instruction TEXT,
                updated_at REAL
            )
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS procedural_habits_key
            ON procedural_habits (session_id, task_type, instruction)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS procedural_habits_task
            ON procedural_habits (task_type)
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    async def record_habit(
        self,
        *,
        habit_id: str,
        session_id: str,
        task_type: str,
        instruction: str,
    ) -> ProceduralHabit:
        updated_at = now()
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO procedural_habits (habit_id, session_id, task_type, instruction, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id, task_type, instruction) DO UPDATE SET
                updated_at = excluded.updated_at
            """,
            (habit_id, session_id, task_type, instruction, updated_at.timestamp()),
        )
        self._trim(cursor)
        self._conn.commit()
        row = cursor.execute(
            """
            SELECT * FROM procedural_habits
            WHERE session_id = ? AND task_type = ? AND instruction = ?
            """,
            (session_id, task_type, instruction),
        ).fetchone()
        if not row:
            return ProceduralHabit(
                habit_id=habit_id,
                session_id=session_id,
                task_type=task_type,
                instruction=instruction,
                updated_at=updated_at,
            )
        return self._row_to_habit(row)

    async def list_habits(
        self,
        *,
        session_id: str | None = None,
        task_type: str | None = None,
    ) -> list[ProceduralHabit]:
        cursor = self._conn.cursor()
        params: list[str] = []
        filters: list[str] = []
        if session_id is not None:
            filters.append("session_id = ?")
            params.append(session_id)
        if task_type is not None:
            filters.append("task_type = ?")
            params.append(task_type)
        where_clause = ""
        if filters:
            where_clause = " WHERE " + " AND ".join(filters)
        rows = cursor.execute(
            f"SELECT * FROM procedural_habits{where_clause} ORDER BY updated_at DESC",
            params,
        ).fetchall()
        return [self._row_to_habit(row) for row in rows]

    def _row_to_habit(self, row: sqlite3.Row) -> ProceduralHabit:
        return ProceduralHabit(
            habit_id=row["habit_id"],
            session_id=row["session_id"],
            task_type=row["task_type"],
            instruction=row["instruction"],
            updated_at=from_timestamp(row["updated_at"]),
        )

    def _trim(self, cursor: sqlite3.Cursor) -> None:
        if self._max_records <= 0:
            return
        cursor.execute(
            """
            DELETE FROM procedural_habits
            WHERE habit_id NOT IN (
                SELECT habit_id FROM procedural_habits
                ORDER BY updated_at DESC
                LIMIT ?
            )
            """,
            (self._max_records,),
        )
