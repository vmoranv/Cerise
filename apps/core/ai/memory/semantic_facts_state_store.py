"""
Semantic facts state store.
"""

from __future__ import annotations

from pathlib import Path

from ...infrastructure import StateStore
from .time_utils import from_timestamp, now
from .types import SemanticFact


class SemanticFactsStateStore:
    """StateStore-backed semantic facts store."""

    def __init__(self, path: str | Path | None, *, max_records: int = 200) -> None:
        self._store = StateStore(path)
        self._key = "semantic_facts"
        self._max_records = max_records

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
        facts = await self._load()
        existing_id = self._find_existing(facts, session_id, subject, predicate)
        resolved_id = existing_id or fact_id
        facts[resolved_id] = {
            "fact_id": resolved_id,
            "session_id": session_id,
            "subject": subject,
            "predicate": predicate,
            "object": object,
            "updated_at": updated_at.timestamp(),
        }
        facts = self._trim(facts)
        await self._store.set(self._key, facts)
        return SemanticFact(
            fact_id=resolved_id,
            session_id=session_id,
            subject=subject,
            predicate=predicate,
            object=object,
            updated_at=updated_at,
        )

    async def list_facts(
        self,
        *,
        session_id: str | None = None,
        subject: str | None = None,
    ) -> list[SemanticFact]:
        facts = await self._load()
        values = [self._entry_to_fact(entry) for entry in facts.values()]
        if session_id is not None:
            values = [fact for fact in values if fact.session_id == session_id]
        if subject is not None:
            values = [fact for fact in values if fact.subject == subject]
        return sorted(values, key=lambda fact: fact.updated_at, reverse=True)

    async def _load(self) -> dict[str, dict]:
        data = await self._store.get(self._key, {})
        if not isinstance(data, dict):
            return {}
        return data

    def _find_existing(self, facts: dict[str, dict], session_id: str, subject: str, predicate: str) -> str | None:
        for fact_id, entry in facts.items():
            if (
                entry.get("session_id") == session_id
                and entry.get("subject") == subject
                and entry.get("predicate") == predicate
            ):
                return fact_id
        return None

    def _trim(self, facts: dict[str, dict]) -> dict[str, dict]:
        if self._max_records <= 0 or len(facts) <= self._max_records:
            return facts
        ordered = sorted(
            facts.items(),
            key=lambda item: float(item[1].get("updated_at", 0.0)),
            reverse=True,
        )
        return dict(ordered[: self._max_records])

    def _entry_to_fact(self, entry: dict) -> SemanticFact:
        return SemanticFact(
            fact_id=entry.get("fact_id", ""),
            session_id=entry.get("session_id", ""),
            subject=entry.get("subject", ""),
            predicate=entry.get("predicate", ""),
            object=entry.get("object", ""),
            updated_at=from_timestamp(float(entry.get("updated_at", 0.0))),
        )
