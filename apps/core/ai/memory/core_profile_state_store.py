"""
Core profile state store.
"""

from __future__ import annotations

from pathlib import Path

from ...infrastructure import StateStore
from .time_utils import from_timestamp, now
from .types import CoreProfile


class CoreProfileStateStore:
    """StateStore-backed core profile store."""

    def __init__(self, path: str | Path | None, *, max_records: int = 200) -> None:
        self._store = StateStore(path)
        self._key = "core_profiles"
        self._max_records = max_records

    async def upsert_profile(
        self,
        *,
        profile_id: str,
        summary: str,
        session_id: str | None = None,
    ) -> CoreProfile:
        updated_at = now()
        profiles = await self._load()
        profiles[profile_id] = {
            "profile_id": profile_id,
            "summary": summary,
            "session_id": session_id,
            "updated_at": updated_at.timestamp(),
        }
        profiles = self._trim(profiles)
        await self._store.set(self._key, profiles)
        return CoreProfile(
            profile_id=profile_id,
            summary=summary,
            session_id=session_id,
            updated_at=updated_at,
        )

    async def get_profile(self, profile_id: str) -> CoreProfile | None:
        profiles = await self._load()
        entry = profiles.get(profile_id)
        if not entry:
            return None
        return self._entry_to_profile(entry)

    async def list_profiles(self, session_id: str | None = None) -> list[CoreProfile]:
        profiles = await self._load()
        values = [self._entry_to_profile(entry) for entry in profiles.values()]
        if session_id is not None:
            values = [profile for profile in values if profile.session_id == session_id]
        return sorted(values, key=lambda profile: profile.updated_at, reverse=True)

    async def _load(self) -> dict[str, dict]:
        data = await self._store.get(self._key, {})
        if not isinstance(data, dict):
            return {}
        return data

    def _trim(self, profiles: dict[str, dict]) -> dict[str, dict]:
        if self._max_records <= 0 or len(profiles) <= self._max_records:
            return profiles
        ordered = sorted(
            profiles.items(),
            key=lambda item: float(item[1].get("updated_at", 0.0)),
            reverse=True,
        )
        return dict(ordered[: self._max_records])

    def _entry_to_profile(self, entry: dict) -> CoreProfile:
        return CoreProfile(
            profile_id=entry.get("profile_id", ""),
            summary=entry.get("summary", ""),
            session_id=entry.get("session_id"),
            updated_at=from_timestamp(float(entry.get("updated_at", 0.0))),
        )
