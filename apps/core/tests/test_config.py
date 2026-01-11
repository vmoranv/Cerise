"""Tests for configuration loading."""

import tempfile
from pathlib import Path

import yaml

from config.loader import ConfigLoader
from config.schemas import (
    AIConfig,
    AppConfig,
    PluginsConfig,
    ProviderConfig,
    ProvidersConfig,
    ServerConfig,
)


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


class TestProviderConfig:
    """Test ProviderConfig schema."""

    def test_create_provider_config(self):
        """Test creating a provider config."""
        config = ProviderConfig(
            id="openai-1",
            type="openai",
            name="OpenAI GPT-4",
            enabled=True,
            config={"api_key": "test-key", "default_model": "gpt-4o"},
        )
        assert config.id == "openai-1"
        assert config.type == "openai"
        assert config.enabled is True
        assert config.config["api_key"] == "test-key"


class TestProvidersConfig:
    """Test ProvidersConfig schema."""

    def test_create_providers_config(self):
        """Test creating providers config with list."""
        config = ProvidersConfig(
            default="openai-1",
            providers=[
                ProviderConfig(
                    id="openai-1",
                    type="openai",
                    name="OpenAI",
                    config={"api_key": "test"},
                )
            ],
        )
        assert config.default == "openai-1"
        assert len(config.providers) == 1


class TestConfigLoader:
    """Test ConfigLoader functionality."""

    def test_load_app_config_from_file(self):
        """Test loading app config from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create subdirs
            (data_dir / "plugins").mkdir()
            (data_dir / "characters").mkdir()
            (data_dir / "logs").mkdir()
            (data_dir / "cache").mkdir()

            config_file = data_dir / "config.yaml"
            config_data = {
                "server": {"host": "localhost", "port": 3000},
                "ai": {"default_provider": "gemini"},
            }
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            loader = ConfigLoader(data_dir)
            config = loader.load_app_config()
            assert config.server.host == "localhost"
            assert config.server.port == 3000
            assert config.ai.default_provider == "gemini"

    def test_load_providers_config_from_file(self):
        """Test loading providers config from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create subdirs
            (data_dir / "plugins").mkdir()
            (data_dir / "characters").mkdir()
            (data_dir / "logs").mkdir()
            (data_dir / "cache").mkdir()

            providers_file = data_dir / "providers.yaml"
            providers_data = {
                "default": "openai-1",
                "providers": [
                    {
                        "id": "openai-1",
                        "type": "openai",
                        "name": "OpenAI",
                        "enabled": True,
                        "config": {"api_key": "sk-test"},
                    }
                ],
            }
            with open(providers_file, "w") as f:
                yaml.dump(providers_data, f)

            loader = ConfigLoader(data_dir)
            config = loader.load_providers_config()
            assert len(config.providers) == 1
            assert config.providers[0].id == "openai-1"
            assert config.providers[0].type == "openai"

    def test_save_app_config(self):
        """Test saving app config to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create subdirs
            (data_dir / "plugins").mkdir()
            (data_dir / "characters").mkdir()
            (data_dir / "logs").mkdir()
            (data_dir / "cache").mkdir()

            loader = ConfigLoader(data_dir)

            config = AppConfig(
                server=ServerConfig(port=5000),
                ai=AIConfig(default_provider="claude"),
            )
            loader.save_app_config(config)

            # Reload and verify
            loaded = loader.load_app_config()
            assert loaded.server.port == 5000
            assert loaded.ai.default_provider == "claude"

    def test_save_providers_config(self):
        """Test saving providers config to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create subdirs
            (data_dir / "plugins").mkdir()
            (data_dir / "characters").mkdir()
            (data_dir / "logs").mkdir()
            (data_dir / "cache").mkdir()

            loader = ConfigLoader(data_dir)

            config = ProvidersConfig(
                default="test-1",
                providers=[
                    ProviderConfig(
                        id="test-1",
                        type="openai",
                        name="Test Provider",
                        enabled=True,
                        config={"api_key": "test"},
                    )
                ],
            )
            loader.save_providers_config(config)

            # Reload and verify
            loaded = loader.load_providers_config()
            assert len(loaded.providers) == 1
            assert loaded.providers[0].id == "test-1"

    def test_add_provider(self):
        """Test adding a provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create subdirs
            (data_dir / "plugins").mkdir()
            (data_dir / "characters").mkdir()
            (data_dir / "logs").mkdir()
            (data_dir / "cache").mkdir()

            loader = ConfigLoader(data_dir)

            # Add a provider
            provider = ProviderConfig(
                id="new-provider",
                type="openai",
                name="New Provider",
                config={"api_key": "test"},
            )
            loader.add_provider(provider)

            # Verify
            config = loader.get_providers_config()
            assert any(p.id == "new-provider" for p in config.providers)

    def test_remove_provider(self):
        """Test removing a provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create subdirs
            (data_dir / "plugins").mkdir()
            (data_dir / "characters").mkdir()
            (data_dir / "logs").mkdir()
            (data_dir / "cache").mkdir()

            loader = ConfigLoader(data_dir)

            # Add a provider first
            provider = ProviderConfig(
                id="to-remove",
                type="openai",
                name="To Remove",
                config={"api_key": "test"},
            )
            loader.add_provider(provider)

            # Now remove it
            result = loader.remove_provider("to-remove")
            assert result is True

            config = loader.get_providers_config()
            assert not any(p.id == "to-remove" for p in config.providers)

    def test_expand_env_vars(self):
        """Test environment variable expansion."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create subdirs
            (data_dir / "plugins").mkdir()
            (data_dir / "characters").mkdir()
            (data_dir / "logs").mkdir()
            (data_dir / "cache").mkdir()

            # Set test env var
            os.environ["TEST_API_KEY"] = "secret-key-123"

            providers_file = data_dir / "providers.yaml"
            providers_data = {
                "default": "test-1",
                "providers": [
                    {
                        "id": "test-1",
                        "type": "openai",
                        "name": "Test",
                        "enabled": True,
                        "config": {"api_key": "${TEST_API_KEY}"},
                    }
                ],
            }
            with open(providers_file, "w") as f:
                yaml.dump(providers_data, f)

            loader = ConfigLoader(data_dir)
            config = loader.load_providers_config()
            assert config.providers[0].config["api_key"] == "secret-key-123"

            # Cleanup
            del os.environ["TEST_API_KEY"]
