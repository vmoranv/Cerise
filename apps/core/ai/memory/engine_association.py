"""
Knowledge graph association helpers.
"""

from __future__ import annotations

from .config import MemoryConfig
from .kg import extract_entities
from .sqlite_store import SqliteKnowledgeGraphStore
from .store import MemoryStore
from .types import MemoryRecord, MemoryResult


class AssociationMixin:
    config: MemoryConfig | None
    kg_store: SqliteKnowledgeGraphStore | None
    store: MemoryStore

    async def _associative_recall(
        self,
        query: str,
        base_results: list[MemoryResult],
        session_id: str | None,
    ) -> list[MemoryResult]:
        if not self.config or not self.kg_store:
            return []
        cfg = self.config.association
        if cfg.max_hops <= 0:
            return []
        entities = self._gather_entities(
            query, base_results, cfg.max_entities, cfg.expand_from_query, cfg.expand_from_results
        )
        if not entities:
            return []

        all_results: list[MemoryResult] = []
        seen_entities = set(entities)
        hop_entities = entities
        for _ in range(cfg.max_hops):
            triples = await self.kg_store.search_related(hop_entities, session_id, cfg.top_k)
            if not triples:
                break
            hop_results, extra_entities = await self._triples_to_results(triples, cfg.include_facts)
            all_results.extend(hop_results)
            new_entities = [entity for entity in extra_entities if entity not in seen_entities]
            if not new_entities:
                break
            seen_entities.update(new_entities)
            hop_entities = new_entities[: cfg.max_entities]
        return all_results

    def _gather_entities(
        self,
        query: str,
        base_results: list[MemoryResult],
        max_entities: int,
        expand_from_query: bool,
        expand_from_results: bool,
    ) -> list[str]:
        entities: list[str] = []
        if expand_from_query:
            entities.extend(extract_entities(query, max_entities=max_entities))
        if expand_from_results:
            for item in base_results[: min(len(base_results), 5)]:
                if len(entities) >= max_entities:
                    break
                more = extract_entities(item.record.content, max_entities=max_entities - len(entities))
                entities.extend(more)
        deduped: list[str] = []
        seen = set()
        for entity in entities:
            if entity in seen:
                continue
            seen.add(entity)
            deduped.append(entity)
            if len(deduped) >= max_entities:
                break
        return deduped

    async def _triples_to_results(
        self,
        triples: list[dict],
        include_facts: bool,
    ) -> tuple[list[MemoryResult], list[str]]:
        results: list[MemoryResult] = []
        entities: list[str] = []
        for triple in triples:
            subject = triple.get("subject", "")
            obj = triple.get("object", "")
            if subject:
                entities.append(subject)
            if obj:
                entities.append(obj)
            memory_id = triple.get("memory_id")
            if memory_id:
                record = await self.store.get(memory_id)
                if record:
                    results.append(MemoryResult(record=record, score=float(triple.get("score", 0.3)) + 0.2))
            if include_facts:
                content = f"Fact: {subject} {triple.get('predicate', '')} {obj}".strip()
                record = MemoryRecord(
                    session_id=triple.get("session_id", ""),
                    role="system",
                    content=content,
                    metadata={
                        "type": "kg",
                        "subject": subject,
                        "predicate": triple.get("predicate", ""),
                        "object": obj,
                        "memory_id": memory_id,
                    },
                )
                results.append(MemoryResult(record=record, score=float(triple.get("score", 0.3))))
        return results, entities
