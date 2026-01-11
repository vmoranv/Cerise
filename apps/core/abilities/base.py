"""
Ability Base Classes and Types

This module defines the abstract base class and types for all abilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AbilityType(Enum):
    """Type of ability"""

    BUILTIN = "builtin"  # Built-in ability
    PLUGIN = "plugin"  # External plugin


class AbilityCategory(Enum):
    """Category of ability"""

    SYSTEM = "system"  # System operations
    MEDIA = "media"  # Media processing
    NETWORK = "network"  # Network requests
    CREATIVE = "creative"  # Creative content
    UTILITY = "utility"  # General utilities
    GAME = "game"  # Game control


@dataclass
class AbilityResult:
    """Result of ability execution"""

    success: bool
    data: Any = None
    error: str | None = None
    emotion_hint: str | None = None  # Hint for character emotion reaction


@dataclass
class AbilityContext:
    """Context for ability execution"""

    user_id: str
    session_id: str
    character_state: dict = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)


class BaseAbility(ABC):
    """Abstract base class for all abilities"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the ability"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description for LLM understanding"""
        pass

    @property
    @abstractmethod
    def ability_type(self) -> AbilityType:
        """Type of ability (builtin or plugin)"""
        pass

    @property
    @abstractmethod
    def category(self) -> AbilityCategory:
        """Category of ability"""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> dict:
        """JSON Schema for parameters"""
        pass

    @property
    def required_permissions(self) -> list[str]:
        """Required permissions for execution"""
        return []

    @abstractmethod
    async def execute(
        self,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        """Execute the ability with given parameters"""
        pass

    async def validate_params(self, params: dict) -> bool:
        """Validate parameters before execution"""
        return True

    async def on_load(self) -> None:
        """Called when ability is loaded"""
        pass

    async def on_unload(self) -> None:
        """Called when ability is unloaded"""
        pass

    def to_tool_schema(self) -> dict:
        """Convert to OpenAI-compatible tool schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }
