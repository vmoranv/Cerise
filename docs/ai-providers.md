# AI Provider 接口规范

## 概述

Cerise 支持多个 AI 服务提供商，通过统一接口实现无缝切换。

---

## Provider 架构

```mermaid
classDiagram
    class BaseProvider {
        <<abstract>>
        +name: str
        +chat(messages, options) ChatResponse
        +stream_chat(messages, options) AsyncIterator
        +get_capabilities() ProviderCapabilities
    }
    
    class OpenAIProvider {
        +name = "openai"
        +models: ["gpt-4o", "gpt-4", "gpt-3.5-turbo"]
    }
    
    class ClaudeProvider {
        +name = "claude"
        +models: ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
    }
    
    class GeminiProvider {
        +name = "gemini"
        +models: ["gemini-pro", "gemini-ultra"]
    }
    
    class OllamaProvider {
        +name = "ollama"
        +models: [dynamic local models]
    }
    
    BaseProvider <|-- OpenAIProvider
    BaseProvider <|-- ClaudeProvider
    BaseProvider <|-- GeminiProvider
    BaseProvider <|-- OllamaProvider
```

---

## 基础接口定义

```python
# apps/core/ai/providers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

@dataclass
class Message:
    """对话消息"""
    role: str  # "system" | "user" | "assistant"
    content: str
    name: str | None = None

@dataclass
class ChatOptions:
    """对话选项"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    stop: list[str] | None = None
    tools: list[dict] | None = None  # Function calling

@dataclass
class ChatResponse:
    """对话响应"""
    content: str
    model: str
    usage: dict[str, int]
    tool_calls: list[dict] | None = None
    finish_reason: str = "stop"

@dataclass
class ProviderCapabilities:
    """Provider 能力描述"""
    streaming: bool = True
    function_calling: bool = False
    vision: bool = False
    max_context_length: int = 4096

class BaseProvider(ABC):
    """AI Provider 抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 标识"""
        pass
    
    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """可用模型列表"""
        pass
    
    @abstractmethod
    async def chat(
        self, 
        messages: list[Message], 
        options: ChatOptions
    ) -> ChatResponse:
        """同步对话"""
        pass
    
    @abstractmethod
    async def stream_chat(
        self, 
        messages: list[Message], 
        options: ChatOptions
    ) -> AsyncIterator[str]:
        """流式对话"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """获取 Provider 能力"""
        pass
    
    async def health_check(self) -> bool:
        """健康检查"""
        return True
```

---

## Provider 实现示例

### OpenAI Provider

```python
# apps/core/ai/providers/openai_provider.py

from openai import AsyncOpenAI
from .base import BaseProvider, Message, ChatOptions, ChatResponse, ProviderCapabilities

class OpenAIProvider(BaseProvider):
    name = "openai"
    available_models = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    
    def __init__(self, api_key: str, base_url: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    async def chat(
        self, 
        messages: list[Message], 
        options: ChatOptions
    ) -> ChatResponse:
        response = await self.client.chat.completions.create(
            model=options.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            tools=options.tools,
        )
        
        return ChatResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
            tool_calls=response.choices[0].message.tool_calls,
            finish_reason=response.choices[0].finish_reason,
        )
    
    async def stream_chat(
        self, 
        messages: list[Message], 
        options: ChatOptions
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=options.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            function_calling=True,
            vision=True,
            max_context_length=128000,
        )
```

### Claude Provider

```python
# apps/core/ai/providers/claude_provider.py

from anthropic import AsyncAnthropic
from .base import BaseProvider, Message, ChatOptions, ChatResponse, ProviderCapabilities

class ClaudeProvider(BaseProvider):
    name = "claude"
    available_models = ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
    
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)
    
    async def chat(
        self, 
        messages: list[Message], 
        options: ChatOptions
    ) -> ChatResponse:
        # 分离 system message
        system_msg = next((m.content for m in messages if m.role == "system"), None)
        chat_messages = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        
        response = await self.client.messages.create(
            model=options.model,
            max_tokens=options.max_tokens,
            system=system_msg,
            messages=chat_messages,
        )
        
        return ChatResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
        )
    
    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            function_calling=True,
            vision=True,
            max_context_length=200000,
        )
```

---

## Provider 注册表

```python
# apps/core/ai/providers/registry.py

from typing import Type
from .base import BaseProvider

class ProviderRegistry:
    """Provider 注册与管理"""
    
    _providers: dict[str, Type[BaseProvider]] = {}
    _instances: dict[str, BaseProvider] = {}
    
    @classmethod
    def register(cls, provider_class: Type[BaseProvider]) -> None:
        """注册 Provider 类"""
        cls._providers[provider_class.name] = provider_class
    
    @classmethod
    def get(cls, name: str) -> BaseProvider:
        """获取 Provider 实例"""
        if name not in cls._instances:
            if name not in cls._providers:
                raise ValueError(f"Unknown provider: {name}")
            # 从配置加载并实例化
            cls._instances[name] = cls._create_instance(name)
        return cls._instances[name]
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """列出所有注册的 Provider"""
        return list(cls._providers.keys())
```

---

## 配置格式

```yaml
# config.yaml

ai:
  default_provider: openai
  default_model: gpt-4o
  
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      base_url: null  # 可选，用于代理
      
    claude:
      api_key: ${ANTHROPIC_API_KEY}
      
    gemini:
      api_key: ${GOOGLE_API_KEY}
      
    ollama:
      base_url: http://localhost:11434
      default_model: llama3
```

---

## 使用示例

```python
from apps.core.ai.providers import ProviderRegistry, Message, ChatOptions

# 获取 Provider
provider = ProviderRegistry.get("openai")

# 对话
messages = [
    Message(role="system", content="你是一个可爱的虚拟主播"),
    Message(role="user", content="你好！"),
]

response = await provider.chat(
    messages,
    ChatOptions(model="gpt-4o", temperature=0.8)
)

print(response.content)

# 流式对话
async for chunk in provider.stream_chat(messages, options):
    print(chunk, end="", flush=True)
```
