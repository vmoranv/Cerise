"""Agent orchestration service (create/send/wakeup)."""

from __future__ import annotations

import time
from uuid import uuid4

from ...contracts.events import (
    AGENT_CREATED,
    AGENT_MESSAGE_CREATED,
    AGENT_WAKEUP_COMPLETED,
    AGENT_WAKEUP_STARTED,
    build_agent_created,
    build_agent_message_created,
    build_agent_wakeup_completed,
    build_agent_wakeup_started,
)
from ...infrastructure import EventBus, StateStore
from ..dialogue.engine import DialogueEngine
from .models import Agent, AgentMessage
from .store import AgentStore


class AgentService:
    def __init__(
        self,
        *,
        store: StateStore,
        bus: EventBus,
        dialogue_engine: DialogueEngine,
    ) -> None:
        self._bus = bus
        self._dialogue = dialogue_engine
        self._store = AgentStore(store)

    async def create(self, *, agent_id: str | None = None, parent_id: str | None = None, name: str = "") -> Agent:
        new_id = agent_id or str(uuid4())
        agent = Agent(id=new_id, parent_id=parent_id, name=name)
        await self._store.upsert_agent(agent)
        await self._bus.emit(AGENT_CREATED, build_agent_created(agent.id, agent.parent_id, agent.name), source="agent")
        return agent

    async def send(self, *, agent_id: str, role: str, content: str) -> AgentMessage:
        message = AgentMessage(id=str(uuid4()), agent_id=agent_id, role=role, content=content)
        await self._store.append_message(agent_id, message)
        if role == "user":
            await self._store.enqueue_inbox(agent_id, message)
        await self._bus.emit(
            AGENT_MESSAGE_CREATED,
            build_agent_message_created(message.id, agent_id, role, content),
            source="agent",
        )
        return message

    async def wakeup(
        self,
        *,
        agent_id: str,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AgentMessage | None:
        pending = await self._store.drain_inbox(agent_id)
        if not pending:
            return None

        await self._bus.emit(
            AGENT_WAKEUP_STARTED,
            build_agent_wakeup_started(agent_id, len(pending)),
            source="agent",
        )

        session = self._dialogue.get_session(agent_id)
        if not session:
            session = self._dialogue.create_session(session_id=agent_id)

        user_text = "\n\n".join(msg.content for msg in pending if msg.content)
        start = time.perf_counter()
        response = await self._dialogue.chat(
            session=session,
            user_message=user_text,
            provider=provider,
            model=model,
            temperature=temperature,
            use_tools=False,
        )
        duration_ms = (time.perf_counter() - start) * 1000

        assistant = AgentMessage(id=str(uuid4()), agent_id=agent_id, role="assistant", content=response)
        await self._store.append_message(agent_id, assistant)
        await self._bus.emit(
            AGENT_MESSAGE_CREATED,
            build_agent_message_created(assistant.id, agent_id, assistant.role, assistant.content),
            source="agent",
        )
        await self._bus.emit(
            AGENT_WAKEUP_COMPLETED,
            build_agent_wakeup_completed(agent_id, assistant.id, round(duration_ms, 2)),
            source="agent",
        )
        return assistant

    async def list_messages(self, agent_id: str, *, limit: int | None = None) -> list[AgentMessage]:
        return await self._store.list_messages(agent_id, limit=limit)

    async def list_agents(self) -> list[Agent]:
        return await self._store.list_agents()
