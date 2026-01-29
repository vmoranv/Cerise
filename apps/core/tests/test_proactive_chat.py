"""Proactive chat scheduling tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest
from apps.core.ai.dialogue.proactive_config import ProactiveChatConfig, ProactiveScheduleConfig
from apps.core.ai.dialogue.proactive_service import ProactiveChatService
from apps.core.ai.dialogue.proactive_state import ProactiveSessionState
from apps.core.contracts.events import DIALOGUE_USER_MESSAGE
from apps.core.infrastructure import Event, MessageBus, StateStore


@dataclass
class StubSession:
    id: str


class StubDialogue:
    def __init__(self) -> None:
        self.sessions: dict[str, StubSession] = {}
        self.calls: list[dict] = []

    def get_session(self, session_id: str) -> StubSession | None:
        return self.sessions.get(session_id)

    def create_session(self, session_id: str) -> StubSession:
        session = StubSession(session_id)
        self.sessions[session_id] = session
        return session

    async def proactive_chat(self, session: StubSession, **kwargs) -> str:
        payload = {"session_id": session.id}
        payload.update(kwargs)
        self.calls.append(payload)
        return "hello"


class CapturingProactiveChatService(ProactiveChatService):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scheduled: list[tuple[str, float, float]] = []

    def _schedule_task(self, session_id: str, delay: float, trigger_at: float) -> None:
        self.scheduled.append((session_id, delay, trigger_at))


@pytest.mark.asyncio
async def test_user_message_updates_state_and_schedules_next() -> None:
    fixed_now = datetime(2025, 1, 1, 10, 0, 0)
    schedule = ProactiveScheduleConfig(
        min_interval_minutes=1,
        max_interval_minutes=1,
        quiet_hours="",
        max_unanswered_times=2,
    )
    config = ProactiveChatConfig(enabled=True, apply_to_all_sessions=True, schedule=schedule)
    service = CapturingProactiveChatService(
        bus=MessageBus(),
        dialogue_engine=StubDialogue(),
        config=config,
        state_store=StateStore(),
        now=lambda: fixed_now,
    )

    event = Event(type=DIALOGUE_USER_MESSAGE, data={"session_id": "s1", "content": "hi"})
    await service._handle_user_message(event)

    state = await service._get_state("s1")
    assert state.last_user_at == fixed_now.timestamp()
    assert state.unanswered_count == 0
    assert service.scheduled

    session_id, delay, trigger_at = service.scheduled[0]
    assert session_id == "s1"
    assert delay == 60.0
    assert trigger_at == fixed_now.timestamp() + 60


@pytest.mark.asyncio
async def test_trigger_session_calls_proactive_chat_and_updates_state() -> None:
    fixed_now = datetime(2025, 1, 1, 10, 0, 0)
    schedule = ProactiveScheduleConfig(
        min_interval_minutes=1,
        max_interval_minutes=1,
        quiet_hours="",
        max_unanswered_times=4,
    )
    config = ProactiveChatConfig(enabled=True, apply_to_all_sessions=True, schedule=schedule)
    dialogue = StubDialogue()
    service = CapturingProactiveChatService(
        bus=MessageBus(),
        dialogue_engine=dialogue,
        config=config,
        state_store=StateStore(),
        now=lambda: fixed_now,
    )

    trigger_at = fixed_now.timestamp()
    await service._set_state("s2", ProactiveSessionState(next_trigger_at=trigger_at))

    await service._trigger_session("s2", trigger_at)

    state = await service._get_state("s2")
    assert state.unanswered_count == 1
    assert dialogue.calls
    assert dialogue.calls[0]["session_id"] == "s2"


@pytest.mark.asyncio
async def test_trigger_session_respects_quiet_hours() -> None:
    quiet_now = datetime(2025, 1, 1, 2, 0, 0)
    schedule = ProactiveScheduleConfig(
        min_interval_minutes=1,
        max_interval_minutes=1,
        quiet_hours="1-7",
        max_unanswered_times=2,
    )
    config = ProactiveChatConfig(enabled=True, apply_to_all_sessions=True, schedule=schedule)
    dialogue = StubDialogue()
    service = CapturingProactiveChatService(
        bus=MessageBus(),
        dialogue_engine=dialogue,
        config=config,
        state_store=StateStore(),
        now=lambda: quiet_now,
    )

    trigger_at = quiet_now.timestamp()
    await service._set_state("s3", ProactiveSessionState(next_trigger_at=trigger_at))

    await service._trigger_session("s3", trigger_at)

    assert not dialogue.calls
    assert service.scheduled

    _, delay, _ = service.scheduled[0]
    assert delay == 5 * 60 * 60
