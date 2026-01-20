"""
Knowledge graph search helpers.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any


class KnowledgeGraphSearchMixin:
    _conn: sqlite3.Connection

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

    async def search_related(self, entities: list[str], session_id: str | None, limit: int) -> list[dict[str, Any]]:
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
