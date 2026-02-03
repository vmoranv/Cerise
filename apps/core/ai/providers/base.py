"""
AI Provider Base Classes

Defines the abstract interface for all AI providers.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class Message:
    """Chat message"""

    role: str  # "system" | "user" | "assistant"
    content: str | list[dict]
    name: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


@dataclass
class ChatOptions:
    """Options for chat completion"""

    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    stop: list[str] | None = None
    tools: list[dict] | None = None
    stream: bool = False


@dataclass
class ChatResponse:
    """Response from chat completion"""

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    tool_calls: list[dict] | None = None
    finish_reason: str = "stop"


@dataclass
class ProviderCapabilities:
    """Capabilities of a provider"""

    chat: bool = True
    streaming: bool = True
    function_calling: bool = False
    vision: bool = False
    embeddings: bool = False
    rerank: bool = False
    max_context_length: int = 4096


class BaseProvider(ABC):
    """Abstract base class for AI providers"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier"""
        pass

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """List of available models"""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> ChatResponse:
        """Synchronous chat completion"""
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> AsyncIterator[str]:
        """Streaming chat completion"""
        pass

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities"""
        pass

    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        return True

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Optional: embedding endpoint."""
        raise NotImplementedError("Embedding is not supported by this provider")

    async def rerank(
        self,
        query: str,
        documents: list[str],
        model: str | None = None,
        top_k: int | None = None,
    ) -> list[tuple[int, float]]:
        """Optional: rerank endpoint."""
        raise NotImplementedError("Rerank is not supported by this provider")
