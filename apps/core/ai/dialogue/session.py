"""
Dialogue Session

Manages conversation history and context.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class Message:
    """A single message in a conversation"""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to API-compatible dict"""
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass
class Session:
    """A conversation session"""

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    messages: list[Message] = field(default_factory=list)
    system_prompt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    max_history: int = 50  # Maximum messages to keep

    def add_message(self, role: str, content: str, **kwargs) -> Message:
        """Add a message to the session"""
        message = Message(role=role, content=content, **kwargs)
        self.messages.append(message)
        self.updated_at = datetime.now()

        # Trim old messages if exceeding limit
        if len(self.messages) > self.max_history:
            # Keep system messages and recent messages
            system_msgs = [m for m in self.messages if m.role == "system"]
            other_msgs = [m for m in self.messages if m.role != "system"]
            keep_count = self.max_history - len(system_msgs)
            self.messages = system_msgs + other_msgs[-keep_count:]

        return message

    def add_user_message(self, content: str) -> Message:
        """Add a user message"""
        return self.add_message("user", content)

    def add_assistant_message(self, content: str, tool_calls: list[dict] | None = None) -> Message:
        """Add an assistant message"""
        return self.add_message("assistant", content, tool_calls=tool_calls)

    def add_tool_result(self, tool_call_id: str, content: str, name: str = "") -> Message:
        """Add a tool result message"""
        return self.add_message("tool", content, tool_call_id=tool_call_id, name=name)

    def get_context_messages(self) -> list[dict]:
        """Get messages formatted for API call"""
        result = []

        # Add system prompt first
        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})

        # Add conversation messages
        for msg in self.messages:
            if msg.role != "system":  # Skip system messages (already added)
                result.append(msg.to_dict())

        return result

    def get_last_message(self, role: str | None = None) -> Message | None:
        """Get the last message, optionally filtered by role"""
        for msg in reversed(self.messages):
            if role is None or msg.role == role:
                return msg
        return None

    def clear_history(self, keep_system: bool = True) -> None:
        """Clear message history"""
        if keep_system:
            self.messages = [m for m in self.messages if m.role == "system"]
        else:
            self.messages = []
        self.updated_at = datetime.now()

    def token_estimate(self) -> int:
        """Rough estimate of token count (4 chars ≈ 1 token)"""
        total = len(self.system_prompt)
        for msg in self.messages:
            total += len(msg.content)
        return total // 4

    def to_dict(self) -> dict:
        """Serialize session"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "system_prompt": self.system_prompt,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Deserialize session"""
        session = cls(
            id=data.get("id", str(uuid4())),
            user_id=data.get("user_id", ""),
            system_prompt=data.get("system_prompt", ""),
            metadata=data.get("metadata", {}),
        )
        for msg_data in data.get("messages", []):
            session.add_message(**msg_data)
        return session
