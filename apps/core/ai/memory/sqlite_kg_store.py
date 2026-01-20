"""
SQLite-backed knowledge graph store.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .sqlite_kg_search import KnowledgeGraphSearchMixin


class SqliteKnowledgeGraphStore(KnowledgeGraphSearchMixin):
    """SQLite store for knowledge graph triples."""

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
            CREATE TABLE IF NOT EXISTS kg_triples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                subject TEXT,
                predicate TEXT,
                object TEXT,
                memory_id TEXT,
                created_at REAL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_kg_session ON kg_triples(session_id)
            """
        )
        try:
            cursor.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS kg_triples_fts
                USING fts5(triple_id, subject, predicate, object, session_id, tokenize='unicode61')
                """
            )
        except sqlite3.OperationalError:
            pass
        self._conn.commit()

    async def add_triples(
        self,
        session_id: str,
        triples: list[tuple[str, str, str]],
        memory_id: str | None = None,
    ) -> None:
        if not triples:
            return
        cursor = self._conn.cursor()
        now = time.time()
        for subj, pred, obj in triples:
            cursor.execute(
                """
                INSERT INTO kg_triples (session_id, subject, predicate, object, memory_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, subj, pred, obj, memory_id, now),
            )
            triple_id = cursor.lastrowid
            try:
                cursor.execute(
                    """
                    INSERT INTO kg_triples_fts (triple_id, subject, predicate, object, session_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (triple_id, subj, pred, obj, session_id),
                )
            except sqlite3.OperationalError:
                pass
        self._conn.commit()
