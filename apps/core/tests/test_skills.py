"""Skill library tests."""

from __future__ import annotations

import pytest
from apps.core.abilities.base import AbilityResult
from apps.core.ai.dialogue.engine import DialogueEngine
from apps.core.ai.providers.base import ChatOptions, ChatResponse, Message, ProviderCapabilities
from apps.core.ai.skills.service import SkillService
from apps.core.infrastructure import MessageBus, StateStore


class CapturingProvider:
    name = "mock"
    available_models = ["mock-model"]

    def __init__(self) -> None:
        self.last_messages: list[Message] | None = None

    async def chat(self, messages: list[Message], options: ChatOptions) -> ChatResponse:
        self.last_messages = messages
        return ChatResponse(content="ok", model=options.model)

    async def stream_chat(self, messages: list[Message], options: ChatOptions):
        yield "ok"

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

    async def execute(self, ability_name: str, params: dict, context) -> AbilityResult:  # noqa: ARG002
        return AbilityResult(success=False, error="not implemented")


@pytest.mark.asyncio
async def test_skill_search_by_token_overlap() -> None:
    store = StateStore()
    skills = SkillService(store=store)

    await skills.upsert(name="google_search", description="Search the web", code="do_search(query)")
    await skills.upsert(name="write_file", description="Write a file", code="write(path, content)")

    results = await skills.search("search query", top_k=2)
    assert results
    assert results[0].name == "google_search"


@pytest.mark.asyncio
async def test_dialogue_engine_injects_skill_block() -> None:
    MessageBus.reset()
    bus = MessageBus()
    await bus.start()

    store = StateStore()
    skill_service = SkillService(store=store)
    await skill_service.upsert(name="google_search", description="Search the web", code="do_search(query)")

    provider = CapturingProvider()
    engine = DialogueEngine(
        message_bus=bus,
        default_provider="mock",
        default_model="mock-model",
        provider_registry=DummyProviderRegistry(provider),
        ability_registry=DummyAbilityRegistry(),
        skill_service=skill_service,
        skill_recall=True,
        skill_top_k=3,
    )

    session = engine.create_session(session_id="s1")
    await engine.chat(session=session, user_message="please search", use_tools=False)

    assert provider.last_messages is not None
    system_messages = [m for m in provider.last_messages if m.role == "system"]
    assert system_messages
    assert any("Skill Library" in (m.content if isinstance(m.content, str) else "") for m in system_messages)
    assert any("google_search" in (m.content if isinstance(m.content, str) else "") for m in system_messages)

    await bus.stop()
    MessageBus.reset()


class ToolCallingProvider:
    name = "mock"
    available_models = ["mock-model"]

    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, messages: list[Message], options: ChatOptions) -> ChatResponse:  # noqa: ARG002
        self.calls += 1
        if self.calls == 1:
            return ChatResponse(
                content="",
                model=options.model,
                tool_calls=[
                    {"id": "tc1", "function": {"name": "demo_tool", "arguments": {"x": 1}}},
                ],
            )
        if self.calls == 2:
            return ChatResponse(
                content="",
                model=options.model,
                tool_calls=[
                    {"id": "tc2", "function": {"name": "demo_tool", "arguments": {"x": 2}}},
                ],
            )
        return ChatResponse(content="done", model=options.model)

    async def stream_chat(self, messages: list[Message], options: ChatOptions):  # noqa: ARG002
        yield "done"

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(streaming=True, function_calling=True)


class ToolAbilityRegistry:
    def __init__(self) -> None:
        self.calls = 0

    def get_tool_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "demo_tool",
                    "description": "Demo tool for tests",
                    "parameters": {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]},
                },
            },
        ]

    async def execute(self, ability_name: str, params: dict, context) -> AbilityResult:  # noqa: ARG002
        assert ability_name == "demo_tool"
        self.calls += 1
        if self.calls == 1:
            return AbilityResult(success=False, error="bad args")
        return AbilityResult(success=True, data=f"ok:{params.get('x')}")


@pytest.mark.asyncio
async def test_tool_failure_feedback_loop_records_runs() -> None:
    MessageBus.reset()
    bus = MessageBus()
    await bus.start()

    store = StateStore()
    skill_service = SkillService(store=store)

    provider = ToolCallingProvider()
    ability_registry = ToolAbilityRegistry()
    engine = DialogueEngine(
        message_bus=bus,
        default_provider="mock",
        default_model="mock-model",
        provider_registry=DummyProviderRegistry(provider),
        ability_registry=ability_registry,
        skill_service=skill_service,
        skill_recall=False,
    )

    session = engine.create_session(session_id="s-tool")
    content = await engine.chat(session=session, user_message="hi", use_tools=True)
    assert content == "done"

    runs = await skill_service.list_tool_runs("s-tool")
    assert len(runs) == 2
    assert runs[0].tool_name == "demo_tool"
    assert runs[0].success is False
    assert runs[1].success is True

    await bus.stop()
    MessageBus.reset()
