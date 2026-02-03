"""Agent storage backed by StateStore."""

from __future__ import annotations

from typing import Any

from ...infrastructure import StateStore
from .models import Agent, AgentMessage


class AgentStore:
    def __init__(self, store: StateStore) -> None:
        self._store = store.create_namespace("agents")

    async def list_agents(self) -> list[Agent]:
        registry = await self._store.get("registry", {})
        if not isinstance(registry, dict):
            return []
        return [Agent.from_dict(item) for item in registry.values() if isinstance(item, dict)]

    async def get_agent(self, agent_id: str) -> Agent | None:
        registry = await self._store.get("registry", {})
        if not isinstance(registry, dict):
            return None
        data = registry.get(agent_id)
        if not isinstance(data, dict):
            return None
        return Agent.from_dict(data)

    async def upsert_agent(self, agent: Agent) -> None:
        registry = await self._store.get("registry", {})
        if not isinstance(registry, dict):
            registry = {}
        registry[agent.id] = agent.to_dict()
        await self._store.set("registry", registry)

    async def append_message(self, agent_id: str, message: AgentMessage, *, keep_last: int = 200) -> None:
        key = f"messages.{agent_id}"
        data = await self._store.get(key, [])
        if not isinstance(data, list):
            data = []
        data.append(message.to_dict())
        if keep_last > 0 and len(data) > keep_last:
            data = data[-keep_last:]
        await self._store.set(key, data)

    async def list_messages(self, agent_id: str, *, limit: int | None = None) -> list[AgentMessage]:
        key = f"messages.{agent_id}"
        data = await self._store.get(key, [])
        if not isinstance(data, list):
            return []
        msgs = [AgentMessage.from_dict(item) for item in data if isinstance(item, dict)]
        if limit and limit > 0:
            return msgs[-limit:]
        return msgs

    async def enqueue_inbox(self, agent_id: str, message: AgentMessage, *, keep_last: int = 200) -> None:
        key = f"inbox.{agent_id}"
        data = await self._store.get(key, [])
        if not isinstance(data, list):
            data = []
        data.append(message.to_dict())
        if keep_last > 0 and len(data) > keep_last:
            data = data[-keep_last:]
        await self._store.set(key, data)

    async def drain_inbox(self, agent_id: str) -> list[AgentMessage]:
        key = f"inbox.{agent_id}"
        data = await self._store.get(key, [])
        await self._store.set(key, [])
        if not isinstance(data, list):
            return []
        return [AgentMessage.from_dict(item) for item in data if isinstance(item, dict)]

    async def peek_inbox_count(self, agent_id: str) -> int:
        key = f"inbox.{agent_id}"
        data = await self._store.get(key, [])
        return len(data) if isinstance(data, list) else 0

    async def set_meta(self, agent_id: str, key: str, value: Any) -> None:
        meta_key = f"meta.{agent_id}.{key}"
        await self._store.set(meta_key, value)

    async def get_meta(self, agent_id: str, key: str, default: Any = None) -> Any:
        meta_key = f"meta.{agent_id}.{key}"
        return await self._store.get(meta_key, default)
