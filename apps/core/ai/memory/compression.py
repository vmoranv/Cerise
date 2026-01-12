"""
Memory compression utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .types import MemoryRecord


@dataclass
class MemoryCompressor:
    """Compress older memories into a summary record."""

    threshold: int
    window: int
    max_chars: int

    def should_compress(self, record_count: int) -> bool:
        return self.threshold > 0 and record_count >= self.threshold

    def select_records(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        candidates = [
            record for record in records if not record.metadata.get("compressed") and not record.metadata.get("summary")
        ]
        if len(candidates) < self.window:
            return []
        return candidates[: self.window]

    def compress(self, records: list[MemoryRecord]) -> MemoryRecord:
        if not records:
            raise ValueError("No records to compress")
        lines = []
        for record in records:
            content = " ".join(record.content.split())
            if len(content) > 160:
                content = content[:157].rstrip() + "..."
            lines.append(f"- [{record.role}] {content}")
        summary = "\n".join(lines)
        if len(summary) > self.max_chars:
            summary = summary[: self.max_chars].rstrip() + "..."

        summary_record = MemoryRecord(
            session_id=records[0].session_id,
            role="system",
            content="Memory Summary:\n" + summary,
            metadata={
                "summary": True,
                "compressed": True,
                "source_ids": [record.id for record in records],
                "source_count": len(records),
                "source_last_at": max(record.created_at for record in records).isoformat(),
                "source_first_at": min(record.created_at for record in records).isoformat(),
                "created_by": "memory_compressor",
            },
            created_at=datetime.utcnow(),
        )
        return summary_record
