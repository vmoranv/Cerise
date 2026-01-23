"""Background memory maintenance helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .config import MemoryConfig
from .store import MemoryStore
from .time_utils import ensure_timezone, now
from .types import MemoryRecord


@dataclass
class MemoryMaintenance:
    """Apply decay and pruning policies to memory records."""

    store: MemoryStore
    config: MemoryConfig

    async def run(self, *, session_id: str | None = None) -> dict[str, int]:
        if not self.config.dreaming.enabled:
            return {"updated": 0, "deleted": 0}
        records = await self.store.list(session_id=session_id)
        if self.config.dreaming.max_records > 0:
            records = records[-self.config.dreaming.max_records :]
        current_time = now()

        updated = 0
        to_delete: list[str] = []
        for record in records:
            score = self._decayed_score(record, current_time)
            record.metadata["decayed_score"] = score
            record.metadata["decayed_at"] = current_time.isoformat()

            importance = float(record.importance or 0) / 100.0
            if score < self.config.dreaming.prune_score_threshold and importance <= self.config.dreaming.min_importance:
                to_delete.append(record.id)
                continue

            expires_at = None
            if self.config.store.ttl_seconds > 0:
                expires_at = record.created_at.timestamp() + self.config.store.ttl_seconds
            await self.store.add(record, expires_at=expires_at)
            updated += 1

        if to_delete:
            await self.store.delete(to_delete)

        return {"updated": updated, "deleted": len(to_delete)}

    def _decayed_score(self, record: MemoryRecord, now: datetime) -> float:
        created_at = ensure_timezone(record.created_at)
        age_seconds = max((now - created_at).total_seconds(), 0.0)
        half_life = max(self.config.dreaming.decay_half_life_seconds, 1)
        decay = 0.5 ** (age_seconds / half_life)

        importance = max(float(record.importance or 0) / 100.0, 0.0)
        emotional = max(float(record.emotional_impact or 0) / 100.0, 0.0)
        access = min(float(record.access_count or 0) / max(self.config.scoring.max_access_count, 1), 1.0)

        base = 0.6 * importance + 0.3 * emotional + 0.1 * access
        return max(base * decay, 0.0)
