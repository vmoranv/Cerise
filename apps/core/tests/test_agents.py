"""Multi-agent service tests."""

from __future__ import annotations

import asyncio

import pytest
from apps.core.ai.agents.service import AgentService
from apps.core.ai.dialogue.engine import DialogueEngine
from apps.core.ai.providers.base import ChatOptions, ChatResponse, Message, ProviderCapabilities
from apps.core.contracts.events import (
    AGENT_CREATED,
    AGENT_MESSAGE_CREATED,
    AGENT_WAKEUP_COMPLETED,
    AGENT_WAKEUP_STARTED,
    DIALOGUE_ASSISTANT_RESPONSE,
    DIALOGUE_USER_MESSAGE,
)
from apps.core.infrastructure import Event, MessageBus, StateStore


class DummyProvider:
    name = "mock"
    available_models = ["mock-model"]

    async def chat(self, messages: list[Message], options: ChatOptions) -> ChatResponse:
        # Find last user message and echo it to make assertions stable.
        last_user = ""
        for msg in reversed(messages):
            if msg.role == "user":
                last_user = msg.content if isinstance(msg.content, str) else ""
                break
        return ChatResponse(content=f"echo:{last_user}", model=options.model)

    async def stream_chat(self, messages: list[Message], options: ChatOptions):
        yield "echo"

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(streaming=True)


class DummyProviderRegistry:
    def __init__(self, provider):
        self._provider = provider

    def get(self, provider_id: str):
        return self._provider if provider_id == "mock" else None


class DummyAbilityRegistry:
    def get_tool_schemas(self) -> list[dict]:
        return []


@pytest.mark.asyncio
async def test_agent_service_create_send_wakeup_emits_events() -> None:
    MessageBus.reset()
    bus = MessageBus()
    await bus.start()

    provider = DummyProvider()
    dialogue = DialogueEngine(
        message_bus=bus,
        default_provider="mock",
        default_model="mock-model",
        provider_registry=DummyProviderRegistry(provider),
        ability_registry=DummyAbilityRegistry(),
    )
    store = StateStore()
    agents = AgentService(store=store, bus=bus, dialogue_engine=dialogue)

    seen: dict[str, list[dict]] = {}
    done = asyncio.Event()

    async def capture(event: Event) -> None:
        seen.setdefault(event.type, []).append(event.data)
        if (
            AGENT_CREATED in seen
            and AGENT_MESSAGE_CREATED in seen
            and AGENT_WAKEUP_STARTED in seen
            and AGENT_WAKEUP_COMPLETED in seen
            and DIALOGUE_USER_MESSAGE in seen
            and DIALOGUE_ASSISTANT_RESPONSE in seen
        ):
            done.set()

    for event_type in (
        AGENT_CREATED,
        AGENT_MESSAGE_CREATED,
        AGENT_WAKEUP_STARTED,
        AGENT_WAKEUP_COMPLETED,
        DIALOGUE_USER_MESSAGE,
        DIALOGUE_ASSISTANT_RESPONSE,
    ):
        bus.subscribe(event_type, capture)

    agent = await agents.create(agent_id="agent-1", name="A")
    assert agent.id == "agent-1"

    await agents.send(agent_id="agent-1", role="user", content="hi")
    reply = await agents.wakeup(agent_id="agent-1")
    assert reply is not None
    assert reply.role == "assistant"
    assert reply.content == "echo:hi"

    await asyncio.wait_for(done.wait(), timeout=2)
    await bus.wait_empty()
    await bus.stop()
    MessageBus.reset()

    assert seen[AGENT_CREATED][0]["agent_id"] == "agent-1"
    assert any(item.get("role") == "user" for item in seen[AGENT_MESSAGE_CREATED])
    assert seen[AGENT_WAKEUP_STARTED][0]["pending_count"] == 1
    assert seen[DIALOGUE_USER_MESSAGE][0]["session_id"] == "agent-1"
    assert seen[DIALOGUE_USER_MESSAGE][0]["content"] == "hi"
