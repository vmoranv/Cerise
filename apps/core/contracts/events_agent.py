"""Agent event contracts."""

from __future__ import annotations

from typing import TypedDict

AGENT_CREATED = "agent.created"
AGENT_MESSAGE_CREATED = "agent.message.created"
AGENT_WAKEUP_STARTED = "agent.wakeup.started"
AGENT_WAKEUP_COMPLETED = "agent.wakeup.completed"


class AgentCreatedPayload(TypedDict):
    agent_id: str
    parent_id: str | None
    name: str


def build_agent_created(agent_id: str, parent_id: str | None = None, name: str = "") -> AgentCreatedPayload:
    return {"agent_id": agent_id, "parent_id": parent_id, "name": name}


class AgentMessageCreatedPayload(TypedDict):
    message_id: str
    agent_id: str
    role: str
    content: str


def build_agent_message_created(message_id: str, agent_id: str, role: str, content: str) -> AgentMessageCreatedPayload:
    return {"message_id": message_id, "agent_id": agent_id, "role": role, "content": content}


class AgentWakeupStartedPayload(TypedDict):
    agent_id: str
    pending_count: int


def build_agent_wakeup_started(agent_id: str, pending_count: int) -> AgentWakeupStartedPayload:
    return {"agent_id": agent_id, "pending_count": pending_count}


class AgentWakeupCompletedPayload(TypedDict):
    agent_id: str
    message_id: str
    duration_ms: float


def build_agent_wakeup_completed(agent_id: str, message_id: str, duration_ms: float) -> AgentWakeupCompletedPayload:
    return {"agent_id": agent_id, "message_id": message_id, "duration_ms": duration_ms}


__all__ = [
    "AGENT_CREATED",
    "AGENT_MESSAGE_CREATED",
    "AGENT_WAKEUP_STARTED",
    "AGENT_WAKEUP_COMPLETED",
    "AgentCreatedPayload",
    "AgentMessageCreatedPayload",
    "AgentWakeupStartedPayload",
    "AgentWakeupCompletedPayload",
    "build_agent_created",
    "build_agent_message_created",
    "build_agent_wakeup_started",
    "build_agent_wakeup_completed",
]
