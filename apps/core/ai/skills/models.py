"""Skill library data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Skill:
    id: str
    name: str
    description: str = ""
    code: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Skill:
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        created_dt = (
            datetime.fromisoformat(created_at) if isinstance(created_at, str) and created_at else datetime.now()
        )
        updated_dt = (
            datetime.fromisoformat(updated_at) if isinstance(updated_at, str) and updated_at else datetime.now()
        )
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            code=str(data.get("code", "")),
            tags=[str(t) for t in (data.get("tags") or []) if t],
            created_at=created_dt,
            updated_at=updated_dt,
        )


@dataclass
class ToolRun:
    """A single tool execution attempt captured during dialogue tool calling."""

    id: str
    session_id: str
    tool_name: str
    tool_call_id: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    success: bool = True
    output: str = ""
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "arguments": dict(self.arguments),
            "provider": self.provider,
            "model": self.model,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ToolRun:
        created_at = data.get("created_at")
        created_dt = (
            datetime.fromisoformat(created_at) if isinstance(created_at, str) and created_at else datetime.now()
        )
        return cls(
            id=str(data.get("id", "")),
            session_id=str(data.get("session_id", "")),
            tool_name=str(data.get("tool_name", "")),
            tool_call_id=data.get("tool_call_id"),
            arguments=dict(data.get("arguments") or {}),
            provider=str(data.get("provider", "")),
            model=str(data.get("model", "")),
            success=bool(data.get("success", True)),
            output=str(data.get("output", "")),
            error=data.get("error"),
            created_at=created_dt,
        )
