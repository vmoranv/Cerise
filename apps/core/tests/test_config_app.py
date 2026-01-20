"""Tests for AppConfig schema."""

from apps.core.config.schemas import AIConfig, AppConfig, PluginsConfig, ServerConfig


class TestAppConfig:
    """Test AppConfig schema."""

    def test_default_values(self):
        """Test default values are set correctly."""
        config = AppConfig()
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8000
        assert config.ai.default_provider == "openai"
        assert config.plugins.enabled is True

    def test_custom_values(self):
        """Test custom values are set correctly."""
        config = AppConfig(
            server=ServerConfig(host="127.0.0.1", port=9000),
            ai=AIConfig(default_provider="claude", default_model="claude-3"),
            plugins=PluginsConfig(enabled=False, auto_start=False),
        )
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 9000
        assert config.ai.default_provider == "claude"
        assert config.plugins.enabled is False
