"""
Semantic facts stores.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .time_utils import from_timestamp, now
from .types import SemanticFact


class SemanticFactsStore:
    """SQLite store for semantic facts."""

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
            CREATE TABLE IF NOT EXISTS semantic_facts (
                fact_id TEXT PRIMARY KEY,
                session_id TEXT,
                subject TEXT,
                predicate TEXT,
                object_value TEXT,
                updated_at REAL
            )
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS semantic_facts_key
            ON semantic_facts (session_id, subject, predicate)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS semantic_facts_subject
            ON semantic_facts (subject)
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    async def upsert_fact(
        self,
        *,
        fact_id: str,
        session_id: str,
        subject: str,
        predicate: str,
        object: str,
    ) -> SemanticFact:
        updated_at = now()
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO semantic_facts (fact_id, session_id, subject, predicate, object_value, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, subject, predicate) DO UPDATE SET
                object_value = excluded.object_value,
                updated_at = excluded.updated_at
            """,
            (fact_id, session_id, subject, predicate, object, updated_at.timestamp()),
        )
        self._trim(cursor)
        self._conn.commit()
        row = cursor.execute(
            """
            SELECT * FROM semantic_facts
            WHERE session_id = ? AND subject = ? AND predicate = ?
            """,
            (session_id, subject, predicate),
        ).fetchone()
        if not row:
            return SemanticFact(
                fact_id=fact_id,
                session_id=session_id,
                subject=subject,
                predicate=predicate,
                object=object,
                updated_at=updated_at,
            )
        return self._row_to_fact(row)

    async def list_facts(
        self,
        *,
        session_id: str | None = None,
        subject: str | None = None,
    ) -> list[SemanticFact]:
        cursor = self._conn.cursor()
        params: list[str] = []
        filters: list[str] = []
        if session_id is not None:
            filters.append("session_id = ?")
            params.append(session_id)
        if subject is not None:
            filters.append("subject = ?")
            params.append(subject)
        where_clause = ""
        if filters:
            where_clause = " WHERE " + " AND ".join(filters)
        rows = cursor.execute(
            f"SELECT * FROM semantic_facts{where_clause} ORDER BY updated_at DESC",
            params,
        ).fetchall()
        return [self._row_to_fact(row) for row in rows]

    def _row_to_fact(self, row: sqlite3.Row) -> SemanticFact:
        return SemanticFact(
            fact_id=row["fact_id"],
            session_id=row["session_id"],
            subject=row["subject"],
            predicate=row["predicate"],
            object=row["object_value"],
            updated_at=from_timestamp(row["updated_at"]),
        )

    def _trim(self, cursor: sqlite3.Cursor) -> None:
        if self._max_records <= 0:
            return
        cursor.execute(
            """
            DELETE FROM semantic_facts
            WHERE fact_id NOT IN (
                SELECT fact_id FROM semantic_facts
                ORDER BY updated_at DESC
                LIMIT ?
            )
            """,
            (self._max_records,),
        )
