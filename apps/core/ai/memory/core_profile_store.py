"""
Core profile stores.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .types import CoreProfile


class CoreProfileStore:
    """SQLite store for core profiles."""

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
            CREATE TABLE IF NOT EXISTS core_profiles (
                profile_id TEXT PRIMARY KEY,
                summary TEXT,
                session_id TEXT,
                updated_at REAL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS core_profiles_session
            ON core_profiles (session_id)
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    async def upsert_profile(
        self,
        *,
        profile_id: str,
        summary: str,
        session_id: str | None = None,
    ) -> CoreProfile:
        updated_at = datetime.utcnow()
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO core_profiles (profile_id, summary, session_id, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET
                summary = excluded.summary,
                session_id = excluded.session_id,
                updated_at = excluded.updated_at
            """,
            (profile_id, summary, session_id, updated_at.timestamp()),
        )
        self._trim(cursor)
        self._conn.commit()
        return CoreProfile(
            profile_id=profile_id,
            summary=summary,
            session_id=session_id,
            updated_at=updated_at,
        )

    async def get_profile(self, profile_id: str) -> CoreProfile | None:
        cursor = self._conn.cursor()
        row = cursor.execute(
            "SELECT * FROM core_profiles WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_profile(row)

    async def list_profiles(self, session_id: str | None = None) -> list[CoreProfile]:
        cursor = self._conn.cursor()
        if session_id:
            rows = cursor.execute(
                """
                SELECT * FROM core_profiles
                WHERE session_id = ?
                ORDER BY updated_at DESC
                """,
                (session_id,),
            ).fetchall()
        else:
            rows = cursor.execute(
                "SELECT * FROM core_profiles ORDER BY updated_at DESC",
            ).fetchall()
        return [self._row_to_profile(row) for row in rows]

    def _row_to_profile(self, row: sqlite3.Row) -> CoreProfile:
        return CoreProfile(
            profile_id=row["profile_id"],
            summary=row["summary"],
            session_id=row["session_id"],
            updated_at=datetime.fromtimestamp(row["updated_at"]),
        )

    def _trim(self, cursor: sqlite3.Cursor) -> None:
        if self._max_records <= 0:
            return
        cursor.execute(
            """
            DELETE FROM core_profiles
            WHERE profile_id NOT IN (
                SELECT profile_id FROM core_profiles
                ORDER BY updated_at DESC
                LIMIT ?
            )
            """,
            (self._max_records,),
        )
