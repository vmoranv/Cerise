"""Agent runtime data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Agent:
    id: str
    parent_id: str | None = None
    name: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Agent:
        created_at = data.get("created_at")
        created_dt = (
            datetime.fromisoformat(created_at) if isinstance(created_at, str) and created_at else datetime.now()
        )
        return cls(
            id=str(data.get("id", "")),
            parent_id=data.get("parent_id"),
            name=str(data.get("name", "")),
            created_at=created_dt,
        )


@dataclass
class AgentMessage:
    id: str
    agent_id: str
    role: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentMessage:
        created_at = data.get("created_at")
        created_dt = (
            datetime.fromisoformat(created_at) if isinstance(created_at, str) and created_at else datetime.now()
        )
        return cls(
            id=str(data.get("id", "")),
            agent_id=str(data.get("agent_id", "")),
            role=str(data.get("role", "")),
            content=str(data.get("content", "")),
            created_at=created_dt,
        )
