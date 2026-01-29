"""
Protocol-specific parameter and result types.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InitializeParams:
    """Parameters for 'initialize' method."""

    plugin_name: str
    config: dict = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)


@dataclass
class InitializeResult:
    """Result for 'initialize' method."""

    success: bool
    abilities: list[dict] = field(default_factory=list)
    skills: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    error: str | None = None


@dataclass
class ExecuteParams:
    """Parameters for 'execute' method."""

    ability: str
    skill: str | None = None
    tool: str | None = None
    name: str | None = None
    params: dict = field(default_factory=dict)
    arguments: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)


@dataclass
class ExecuteResult:
    """Result for 'execute' method."""

    success: bool
    data: Any = None
    error: str | None = None
    emotion_hint: str | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "emotion_hint": self.emotion_hint,
        }


@dataclass
class HealthResult:
    """Result for 'health' method."""

    healthy: bool
    message: str = ""


class Methods:
    """Standard method names."""

    INITIALIZE = "initialize"
    EXECUTE = "execute"
    HEALTH = "health"
    SHUTDOWN = "shutdown"

    # Plugin -> Core notifications
    EVENT = "event"
    LOG = "log"
