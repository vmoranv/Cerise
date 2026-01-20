"""
Provider registry access helpers.
"""

from typing import TYPE_CHECKING

from .base import BaseProvider, ChatOptions, Message

if TYPE_CHECKING:
    from ...config import ProviderConfig


class ProviderRegistryAccessMixin:
    _provider_types: dict[str, type[BaseProvider]]
    _instances: dict[str, BaseProvider]
    _configs: dict[str, "ProviderConfig"]
    _default_provider: str | None
    _initialized: bool

    @classmethod
    def create_instance(
        cls,
        provider_id: str,
        provider_type: str,
        **kwargs,
    ) -> BaseProvider:
        """Create and cache a provider instance manually."""
        if provider_type not in cls._provider_types:
            raise ValueError(f"Unknown provider type: {provider_type}")

        instance = cls._provider_types[provider_type](**kwargs)
        cls._instances[provider_id] = instance

        return instance

    @classmethod
    def get(cls, provider_id: str) -> BaseProvider | None:
        """Get a cached provider instance by ID."""
        if not cls._initialized:
            cls.load_from_config()
        return cls._instances.get(provider_id)

    @classmethod
    def get_default(cls) -> BaseProvider | None:
        """Get the default provider."""
        if not cls._initialized:
            cls.load_from_config()
        if cls._default_provider:
            return cls.get(cls._default_provider)
        return None

    @classmethod
    def set_default(cls, provider_id: str) -> None:
        """Set the default provider."""
        if provider_id not in cls._instances:
            raise ValueError(f"Provider not instantiated: {provider_id}")
        cls._default_provider = provider_id

    @classmethod
    def list_types(cls) -> list[str]:
        """List all registered provider types."""
        return list(cls._provider_types.keys())

    @classmethod
    def list_instances(cls) -> list[str]:
        """List all instantiated providers."""
        if not cls._initialized:
            cls.load_from_config()
        return list(cls._instances.keys())

    @classmethod
    def list_providers(cls) -> list[str]:
        """Alias for list_instances for backward compatibility."""
        return cls.list_instances()

    @classmethod
    def get_provider_info(cls, provider_id: str) -> dict | None:
        """Get provider info including config and capabilities."""
        if provider_id not in cls._instances:
            return None

        instance = cls._instances[provider_id]
        config = cls._configs.get(provider_id)
        capabilities = instance.get_capabilities()

        return {
            "id": provider_id,
            "type": config.type if config else instance.name,
            "name": config.name if config else provider_id,
            "enabled": config.enabled if config else True,
            "models": instance.available_models,
            "capabilities": {
                "chat": capabilities.chat,
                "streaming": capabilities.streaming,
                "function_calling": capabilities.function_calling,
                "vision": capabilities.vision,
                "embeddings": capabilities.embeddings,
                "rerank": capabilities.rerank,
                "max_context_length": capabilities.max_context_length,
            },
        }

    @classmethod
    def _resolve_model_for_provider(cls, provider_id: str, instance: BaseProvider) -> str | None:
        """Pick a model using provider config first, then available models."""
        config = cls._configs.get(provider_id)
        if config:
            configured_model = config.config.get("model")
            if isinstance(configured_model, str) and configured_model:
                return configured_model
            configured_models = config.config.get("models")
            if isinstance(configured_models, list) and configured_models:
                first_model = configured_models[0]
                if isinstance(first_model, str) and first_model:
                    return first_model
        if instance.available_models:
            return instance.available_models[0]
        return None

    @classmethod
    async def test_connection(cls, provider_id: str) -> dict:
        """Test provider connection by sending a simple request."""
        import time

        if provider_id not in cls._instances:
            return {"status": "error", "error": "Provider not found"}

        instance = cls._instances[provider_id]
        capabilities = instance.get_capabilities()
        if not capabilities.chat:
            if capabilities.embeddings:
                try:
                    await instance.embed(["ping"])
                    return {"status": "ok", "latency_ms": 0.0, "model": "embedding"}
                except Exception as exc:
                    return {"status": "error", "error": str(exc)}
            if capabilities.rerank:
                try:
                    await instance.rerank("ping", ["ping"])
                    return {"status": "ok", "latency_ms": 0.0, "model": "rerank"}
                except Exception as exc:
                    return {"status": "error", "error": str(exc)}
            return {"status": "error", "error": "Provider does not support chat/embed/rerank"}
        model = cls._resolve_model_for_provider(provider_id, instance)
        if not model:
            return {"status": "error", "error": "No model configured for provider"}

        try:
            start = time.perf_counter()

            messages = [Message(role="user", content="Hi")]
            options = ChatOptions(
                model=model,
                max_tokens=5,
                temperature=0,
            )

            response = await instance.chat(messages, options)
            latency = (time.perf_counter() - start) * 1000

            return {
                "status": "ok",
                "latency_ms": round(latency, 2),
                "model": response.model,
            }

        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
            }

    @classmethod
    async def health_check_all(cls) -> dict[str, bool]:
        """Check health of all providers."""
        results = {}
        for provider_id, instance in cls._instances.items():
            try:
                results[provider_id] = await instance.health_check()
            except Exception:
                results[provider_id] = False
        return results

    @classmethod
    def reload(cls) -> None:
        """Reload providers from configuration."""
        cls.clear()
        cls.load_from_config()

    @classmethod
    def clear(cls) -> None:
        """Clear all instances."""
        cls._instances.clear()
        cls._configs.clear()
        cls._default_provider = None
        cls._initialized = False
