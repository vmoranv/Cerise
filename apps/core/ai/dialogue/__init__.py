# Dialogue Module

"""
Dialogue engine for conversation management
"""

from .engine import DialogueEngine
from .proactive_config import ProactiveChatConfig, ProactiveSessionConfig, load_proactive_config
from .proactive_service import ProactiveChatService
from .session import Message, Session

__all__ = [
    "DialogueEngine",
    "ProactiveChatConfig",
    "ProactiveSessionConfig",
    "ProactiveChatService",
    "load_proactive_config",
    "Session",
    "Message",
]
