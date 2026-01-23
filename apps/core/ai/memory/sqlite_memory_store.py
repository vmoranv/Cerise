"""
SQLite-backed memory store.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from .time_utils import ensure_timezone, from_timestamp, now
from .types import MemoryRecord


class SqliteMemoryStore:
    """SQLite store for memory records with FTS5."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path.as_posix(), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                metadata TEXT,
                created_at REAL,
                expires_at REAL
            )
            """
        )
        try:
            cursor.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(id, content, session_id, tokenize='unicode61')
                """
            )
        except sqlite3.OperationalError:
            pass
        self._conn.commit()

    def _now(self) -> float:
        return time.time()

    def close(self) -> None:
        self._conn.close()

    def _purge_expired(self) -> None:
        cursor = self._conn.cursor()
        now = self._now()
        cursor.execute(
            "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now,),
        )
        try:
            cursor.execute("DELETE FROM memories_fts WHERE id NOT IN (SELECT id FROM memories)")
        except sqlite3.OperationalError:
            pass
        self._conn.commit()

    async def add(self, record: MemoryRecord, expires_at: float | None = None) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO memories (id, session_id, role, content, metadata, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.session_id,
                record.role,
                record.content,
                json.dumps(record.metadata, ensure_ascii=False),
                record.created_at.timestamp(),
                expires_at,
            ),
        )
        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO memories_fts (id, content, session_id)
                VALUES (?, ?, ?)
                """,
                (record.id, record.content, record.session_id),
            )
        except sqlite3.OperationalError:
            pass
        self._conn.commit()

    async def get(self, record_id: str) -> MemoryRecord | None:
        self._purge_expired()
        cursor = self._conn.cursor()
        row = cursor.execute(
            "SELECT * FROM memories WHERE id = ?",
            (record_id,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    async def list(self, session_id: str | None = None) -> list[MemoryRecord]:
        self._purge_expired()
        cursor = self._conn.cursor()
        if session_id:
            rows = cursor.execute(
                "SELECT * FROM memories WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM memories ORDER BY created_at ASC").fetchall()
        return [self._row_to_record(row) for row in rows]

    async def delete(self, record_ids: list[str]) -> None:
        if not record_ids:
            return
        cursor = self._conn.cursor()
        cursor.executemany("DELETE FROM memories WHERE id = ?", [(rid,) for rid in record_ids])
        try:
            cursor.executemany("DELETE FROM memories_fts WHERE id = ?", [(rid,) for rid in record_ids])
        except sqlite3.OperationalError:
            pass
        self._conn.commit()

    async def count(self, session_id: str | None = None) -> int:
        self._purge_expired()
        cursor = self._conn.cursor()
        if session_id:
            row = cursor.execute(
                "SELECT COUNT(1) AS count FROM memories WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        else:
            row = cursor.execute(
                "SELECT COUNT(1) AS count FROM memories",
            ).fetchone()
        return int(row["count"]) if row else 0

    async def touch(self, record_id: str, *, accessed_at: datetime | None = None) -> None:
        cursor = self._conn.cursor()
        row = cursor.execute(
            "SELECT metadata FROM memories WHERE id = ?",
            (record_id,),
        ).fetchone()
        if not row:
            return
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        current_time = ensure_timezone(accessed_at) if accessed_at else now()
        access_count = metadata.get("access_count")
        try:
            access_count = int(access_count) if access_count is not None else 0
        except (TypeError, ValueError):
            access_count = 0
        metadata["access_count"] = access_count + 1
        metadata["last_accessed"] = current_time.isoformat()
        cursor.execute(
            "UPDATE memories SET metadata = ? WHERE id = ?",
            (json.dumps(metadata, ensure_ascii=False), record_id),
        )
        self._conn.commit()

    def supports_fts(self) -> bool:
        cursor = self._conn.cursor()
        try:
            cursor.execute("SELECT count(*) FROM memories_fts")
            return True
        except sqlite3.OperationalError:
            return False

    def search_fts(self, query: str, session_id: str | None, limit: int) -> list[tuple[str, float]]:
        self._purge_expired()
        cursor = self._conn.cursor()
        if session_id:
            rows = cursor.execute(
                """
                SELECT memories_fts.id AS id, bm25(memories_fts) AS score
                FROM memories_fts
                WHERE memories_fts MATCH ? AND session_id = ?
                ORDER BY score ASC
                LIMIT ?
                """,
                (query, session_id, limit),
            ).fetchall()
        else:
            rows = cursor.execute(
                """
                SELECT memories_fts.id AS id, bm25(memories_fts) AS score
                FROM memories_fts
                WHERE memories_fts MATCH ?
                ORDER BY score ASC
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        results = []
        for row in rows:
            results.append((row["id"], max(0.0, 1.0 / (1.0 + row["score"]))))
        return results

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        record = MemoryRecord(
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            metadata=metadata,
        )
        record.id = row["id"]
        record.created_at = from_timestamp(row["created_at"])
        return record
