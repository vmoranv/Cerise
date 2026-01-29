"""State models for proactive chat."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProactiveSessionState:
    """State for proactive chat scheduling."""

    last_user_at: float | None = None
    unanswered_count: int = 0
    next_trigger_at: float | None = None

    @classmethod
    def from_dict(cls, data: dict) -> ProactiveSessionState:
        return cls(
            last_user_at=data.get("last_user_at"),
            unanswered_count=int(data.get("unanswered_count", 0)),
            next_trigger_at=data.get("next_trigger_at"),
        )

    def to_dict(self) -> dict:
        return {
            "last_user_at": self.last_user_at,
            "unanswered_count": self.unanswered_count,
            "next_trigger_at": self.next_trigger_at,
        }
