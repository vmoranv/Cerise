"""Skill storage backed by StateStore."""

from __future__ import annotations

from ...infrastructure import StateStore
from .models import Skill, ToolRun


class SkillStore:
    def __init__(self, store: StateStore) -> None:
        self._store = store.create_namespace("skills")

    async def list_skills(self) -> list[Skill]:
        registry = await self._store.get("registry", {})
        if not isinstance(registry, dict):
            return []
        return [Skill.from_dict(item) for item in registry.values() if isinstance(item, dict)]

    async def get_skill(self, skill_id: str) -> Skill | None:
        registry = await self._store.get("registry", {})
        if not isinstance(registry, dict):
            return None
        data = registry.get(skill_id)
        if not isinstance(data, dict):
            return None
        return Skill.from_dict(data)

    async def upsert_skill(self, skill: Skill) -> None:
        registry = await self._store.get("registry", {})
        if not isinstance(registry, dict):
            registry = {}
        registry[skill.id] = skill.to_dict()
        await self._store.set("registry", registry)

    async def delete_skill(self, skill_id: str) -> bool:
        registry = await self._store.get("registry", {})
        if not isinstance(registry, dict):
            return False
        if skill_id not in registry:
            return False
        del registry[skill_id]
        await self._store.set("registry", registry)
        return True


class ToolRunStore:
    def __init__(self, store: StateStore) -> None:
        self._store = store.create_namespace("skills")

    async def append(self, session_id: str, run: ToolRun, *, keep_last: int = 200) -> None:
        key = f"tool_runs.{session_id}"
        data = await self._store.get(key, [])
        if not isinstance(data, list):
            data = []
        data.append(run.to_dict())
        if keep_last > 0 and len(data) > keep_last:
            data = data[-keep_last:]
        await self._store.set(key, data)

    async def list(self, session_id: str, *, limit: int | None = None) -> list[ToolRun]:
        key = f"tool_runs.{session_id}"
        data = await self._store.get(key, [])
        if not isinstance(data, list):
            return []
        runs = [ToolRun.from_dict(item) for item in data if isinstance(item, dict)]
        if limit and limit > 0:
            return runs[-limit:]
        return runs

    async def clear(self, session_id: str) -> None:
        key = f"tool_runs.{session_id}"
        await self._store.set(key, [])
