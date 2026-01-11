"""Tests for provider registry."""

import pytest

from ai.providers.base import BaseProvider
from ai.providers.registry import ProviderRegistry


class TestProviderRegistry:
    """Test ProviderRegistry functionality."""

    def setup_method(self):
        """Reset registry before each test."""
        ProviderRegistry.clear()

    def test_register_provider_type(self):
        """Test registering a provider type."""

        class MockProvider(BaseProvider):
            name = "mock"
            available_models = ["mock-model"]

            async def chat(self, messages, options):
                pass

            async def stream_chat(self, messages, options):
                yield "mock"

        ProviderRegistry.register_type("mock", MockProvider)
        assert "mock" in ProviderRegistry._provider_types

    def test_list_types(self):
        """Test listing provider types."""
        # Register built-in types first
        ProviderRegistry._register_builtin_providers()
        types = ProviderRegistry.list_types()
        assert isinstance(types, list)
        assert "openai" in types

    def test_create_instance(self):
        """Test creating a provider instance manually."""
        # Need to register types first
        ProviderRegistry._register_builtin_providers()

        # Create instance with mock API key (won't actually connect)
        instance = ProviderRegistry.create_instance(
            provider_id="test-openai",
            provider_type="openai",
            api_key="test-key",
        )

        assert "test-openai" in ProviderRegistry._instances
        assert instance is not None

    def test_get_provider_not_initialized(self):
        """Test get returns None for non-existent provider when not loading from config."""
        ProviderRegistry._initialized = True  # Skip auto-loading
        result = ProviderRegistry.get("non-existent")
        assert result is None

    def test_list_instances_empty(self):
        """Test listing instances when empty."""
        ProviderRegistry._initialized = True  # Skip auto-loading
        instances = ProviderRegistry.list_instances()
        assert instances == []

    def test_set_default(self):
        """Test setting default provider."""
        ProviderRegistry._register_builtin_providers()

        # Create an instance first
        ProviderRegistry.create_instance(
            provider_id="test-default",
            provider_type="openai",
            api_key="test-key",
        )

        ProviderRegistry.set_default("test-default")
        assert ProviderRegistry._default_provider == "test-default"

    def test_set_default_not_instantiated(self):
        """Test setting default to non-existent provider raises error."""
        ProviderRegistry._initialized = True

        with pytest.raises(ValueError, match="not instantiated"):
            ProviderRegistry.set_default("non-existent")

    def test_clear(self):
        """Test clearing the registry."""
        ProviderRegistry._register_builtin_providers()
        ProviderRegistry.create_instance(
            provider_id="to-clear",
            provider_type="openai",
            api_key="test",
        )

        ProviderRegistry.clear()

        assert len(ProviderRegistry._instances) == 0
        assert ProviderRegistry._initialized is False


class TestProviderRegistryAsync:
    """Async tests for ProviderRegistry."""

    def setup_method(self):
        """Reset registry before each test."""
        ProviderRegistry.clear()

    @pytest.mark.asyncio
    async def test_test_connection_no_provider(self):
        """Test connection test with non-existent provider."""
        ProviderRegistry._initialized = True  # Skip auto-loading
        result = await ProviderRegistry.test_connection("non-existent")
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_health_check_all_empty(self):
        """Test health check when no providers."""
        ProviderRegistry._initialized = True
        results = await ProviderRegistry.health_check_all()
        assert results == {}
