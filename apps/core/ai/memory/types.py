"""
Memory types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class MemoryRecord:
    """Single memory record."""

    session_id: str
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class MemoryResult:
    """Memory recall result with score."""

    record: MemoryRecord
    score: float
