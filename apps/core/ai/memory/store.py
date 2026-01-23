"""
Memory storage backends.
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from typing import Protocol

from ...infrastructure import StateStore
from .time_utils import from_timestamp, now_timestamp
from .types import MemoryRecord


class MemoryStore(Protocol):
    """Protocol for memory storage backends."""

    async def add(self, record: MemoryRecord, expires_at: float | None = None) -> None:
        """Add a memory record."""

    async def get(self, record_id: str) -> MemoryRecord | None:
        """Get a memory record by id."""

    async def list(self, session_id: str | None = None) -> list[MemoryRecord]:
        """List stored memories, optionally filtered by session."""

    async def delete(self, record_ids: list[str]) -> None:
        """Delete memories by ids."""

    async def count(self, session_id: str | None = None) -> int:
        """Count memories."""

    async def touch(self, record_id: str, *, accessed_at: datetime | None = None) -> None:
        """Update access metadata for a record."""


class InMemoryStore:
    """In-memory memory store with a bounded history."""

    def __init__(self, max_records: int = 1000):
        self._records: deque[tuple[MemoryRecord, float | None]] = deque(maxlen=max_records)
        self._lock = asyncio.Lock()

    async def add(self, record: MemoryRecord, expires_at: float | None = None) -> None:
        async with self._lock:
            self._records = deque(
                [(existing, exp) for existing, exp in self._records if existing.id != record.id],
                maxlen=self._records.maxlen,
            )
            self._records.append((record, expires_at))

    async def get(self, record_id: str) -> MemoryRecord | None:
        async with self._lock:
            self._purge_expired_locked()
            for record, _ in self._records:
                if record.id == record_id:
                    return record
            return None

    async def list(self, session_id: str | None = None) -> list[MemoryRecord]:
        async with self._lock:
            self._purge_expired_locked()
            if not session_id:
                return [record for record, _ in self._records]
            return [record for record, _ in self._records if record.session_id == session_id]

    async def delete(self, record_ids: list[str]) -> None:
        if not record_ids:
            return
        ids = set(record_ids)
        async with self._lock:
            self._records = deque(
                [(record, expires_at) for record, expires_at in self._records if record.id not in ids],
                maxlen=self._records.maxlen,
            )

    async def count(self, session_id: str | None = None) -> int:
        async with self._lock:
            self._purge_expired_locked()
            if not session_id:
                return len(self._records)
            return sum(1 for record, _ in self._records if record.session_id == session_id)

    async def touch(self, record_id: str, *, accessed_at: datetime | None = None) -> None:
        async with self._lock:
            self._purge_expired_locked()
            updated: deque[tuple[MemoryRecord, float | None]] = deque(maxlen=self._records.maxlen)
            for record, expires_at in self._records:
                if record.id == record_id:
                    record.touch(accessed_at)
                updated.append((record, expires_at))
            self._records = updated

    def _purge_expired_locked(self) -> None:
        now = now_timestamp()
        if not self._records:
            return
        self._records = deque(
            [(record, expires_at) for record, expires_at in self._records if expires_at is None or expires_at > now],
            maxlen=self._records.maxlen,
        )


class StateStoreMemoryStore:
    """StateStore-backed memory store."""

    def __init__(self, storage_path: str):
        self._store = StateStore(storage_path)
        self._records_key = "memory.records"

    async def add(self, record: MemoryRecord, expires_at: float | None = None) -> None:
        records = await self._load_records()
        records[record.id] = self._record_to_dict(record, expires_at)
        await self._store.set(self._records_key, records)

    async def get(self, record_id: str) -> MemoryRecord | None:
        records = await self._load_records()
        entry = records.get(record_id)
        if not entry:
            return None
        if self._is_expired(entry):
            await self.delete([record_id])
            return None
        return self._record_from_dict(entry)

    async def list(self, session_id: str | None = None) -> list[MemoryRecord]:
        records = await self._load_records()
        filtered: list[MemoryRecord] = []
        expired: list[str] = []
        for record_id, entry in records.items():
            if self._is_expired(entry):
                expired.append(record_id)
                continue
            if session_id and entry.get("session_id") != session_id:
                continue
            filtered.append(self._record_from_dict(entry))
        if expired:
            await self.delete(expired)
        filtered.sort(key=lambda record: record.created_at)
        return filtered

    async def delete(self, record_ids: list[str]) -> None:
        if not record_ids:
            return
        records = await self._load_records()
        for record_id in record_ids:
            records.pop(record_id, None)
        await self._store.set(self._records_key, records)

    async def count(self, session_id: str | None = None) -> int:
        records = await self._load_records()
        count = 0
        expired: list[str] = []
        for record_id, entry in records.items():
            if self._is_expired(entry):
                expired.append(record_id)
                continue
            if session_id and entry.get("session_id") != session_id:
                continue
            count += 1
        if expired:
            await self.delete(expired)
        return count

    async def touch(self, record_id: str, *, accessed_at: datetime | None = None) -> None:
        records = await self._load_records()
        entry = records.get(record_id)
        if not entry:
            return
        record = self._record_from_dict(entry)
        record.touch(accessed_at)
        expires_at = entry.get("expires_at")
        records[record_id] = self._record_to_dict(record, expires_at)
        await self._store.set(self._records_key, records)

    async def _load_records(self) -> dict[str, dict]:
        records = await self._store.get(self._records_key, {})
        if not isinstance(records, dict):
            return {}
        return records

    def _record_to_dict(self, record: MemoryRecord, expires_at: float | None) -> dict:
        return {
            "id": record.id,
            "session_id": record.session_id,
            "role": record.role,
            "content": record.content,
            "metadata": record.metadata,
            "created_at": record.created_at.timestamp(),
            "expires_at": expires_at,
        }

    def _record_from_dict(self, data: dict) -> MemoryRecord:
        record = MemoryRecord(
            session_id=data.get("session_id", ""),
            role=data.get("role", ""),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}) or {},
        )
        record.id = data.get("id", record.id)
        created_at = data.get("created_at")
        if created_at:
            record.created_at = from_timestamp(float(created_at))
        return record

    def _is_expired(self, data: dict) -> bool:
        expires_at = data.get("expires_at")
        if expires_at is None:
            return False
        return float(expires_at) <= now_timestamp()
