"""Composite memory extractor."""

from __future__ import annotations

from .extraction_types import MemoryExtraction, MemoryExtractor
from .types import MemoryRecord


class CompositeMemoryExtractor:
    """Chain multiple extractors into one."""

    def __init__(self, extractors: list[MemoryExtractor]) -> None:
        self._extractors = [extractor for extractor in extractors if extractor]

    async def extract(self, *, record: MemoryRecord) -> MemoryExtraction:
        extraction = MemoryExtraction()
        for extractor in self._extractors:
            result = await extractor.extract(record=record)
            extraction.core_updates.extend(result.core_updates)
            extraction.facts.extend(result.facts)
            extraction.habits.extend(result.habits)
        return extraction
