"""
SQLite-backed memory store and knowledge graph.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

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
            # FTS5 not available; fallback handled by retriever.
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
            # bm25 returns lower score for more relevant, invert to positive
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
        record.created_at = datetime.fromtimestamp(row["created_at"])
        return record


class SqliteKnowledgeGraphStore:
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

    def supports_fts(self) -> bool:
        cursor = self._conn.cursor()
        try:
            cursor.execute("SELECT count(*) FROM kg_triples_fts")
            return True
        except sqlite3.OperationalError:
            return False

    async def search(self, query: str, session_id: str | None, limit: int) -> list[dict[str, Any]]:
        if not query:
            return []
        if self.supports_fts():
            return self._search_fts(query, session_id, limit)
        tokens = {token for token in re.findall(r"[A-Za-z0-9']+|[\u4e00-\u9fff]", query.lower()) if token}
        if not tokens:
            return []
        cursor = self._conn.cursor()
        if session_id:
            rows = cursor.execute(
                "SELECT * FROM kg_triples WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM kg_triples").fetchall()
        scored = []
        for row in rows:
            subject = row["subject"].lower()
            obj = row["object"].lower()
            score = 0.0
            for token in tokens:
                if token in subject:
                    score += 1.0
                if token in obj:
                    score += 0.8
            if score:
                scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, row in scored[:limit]:
            results.append(
                {
                    "triple_id": row["id"],
                    "session_id": row["session_id"],
                    "subject": row["subject"],
                    "predicate": row["predicate"],
                    "object": row["object"],
                    "memory_id": row["memory_id"],
                    "score": score,
                }
            )
        return results

    def _search_fts(self, query: str, session_id: str | None, limit: int) -> list[dict[str, Any]]:
        cursor = self._conn.cursor()
        if session_id:
            rows = cursor.execute(
                """
                SELECT kg_triples.id AS id, kg_triples.session_id AS session_id,
                       kg_triples.subject AS subject, kg_triples.predicate AS predicate,
                       kg_triples.object AS object, kg_triples.memory_id AS memory_id,
                       bm25(kg_triples_fts) AS score
                FROM kg_triples_fts
                JOIN kg_triples ON kg_triples_fts.triple_id = kg_triples.id
                WHERE kg_triples_fts MATCH ? AND kg_triples.session_id = ?
                ORDER BY score ASC
                LIMIT ?
                """,
                (query, session_id, limit),
            ).fetchall()
        else:
            rows = cursor.execute(
                """
                SELECT kg_triples.id AS id, kg_triples.session_id AS session_id,
                       kg_triples.subject AS subject, kg_triples.predicate AS predicate,
                       kg_triples.object AS object, kg_triples.memory_id AS memory_id,
                       bm25(kg_triples_fts) AS score
                FROM kg_triples_fts
                JOIN kg_triples ON kg_triples_fts.triple_id = kg_triples.id
                WHERE kg_triples_fts MATCH ?
                ORDER BY score ASC
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "triple_id": row["id"],
                    "session_id": row["session_id"],
                    "subject": row["subject"],
                    "predicate": row["predicate"],
                    "object": row["object"],
                    "memory_id": row["memory_id"],
                    "score": max(0.0, 1.0 / (1.0 + row["score"])),
                }
            )
        return results

    async def search_related(
        self,
        entities: list[str],
        session_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not entities:
            return []
        cursor = self._conn.cursor()
        clauses = []
        params: list[Any] = []
        for entity in entities:
            clauses.append("(subject LIKE ? OR object LIKE ?)")
            like = f"%{entity}%"
            params.extend([like, like])
        where = " OR ".join(clauses)
        if session_id:
            params.append(session_id)
            query = f"""
                SELECT * FROM kg_triples
                WHERE ({where}) AND session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """
        else:
            query = f"""
                SELECT * FROM kg_triples
                WHERE ({where})
                ORDER BY created_at DESC
                LIMIT ?
            """
        params.append(limit)
        rows = cursor.execute(query, params).fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "triple_id": row["id"],
                    "session_id": row["session_id"],
                    "subject": row["subject"],
                    "predicate": row["predicate"],
                    "object": row["object"],
                    "memory_id": row["memory_id"],
                    "score": 0.4,
                }
            )
        return results
