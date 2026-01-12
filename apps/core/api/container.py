"""
Service container wiring for the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..abilities import AbilityRegistry
from ..ai import DialogueEngine, EmotionAnalyzer
from ..ai.emotion import EmotionConfigManager
from ..ai.memory import MemoryEngine, MemoryEventHandler, load_memory_config
from ..ai.providers import ProviderRegistry
from ..character import EmotionStateMachine, PersonalityModel
from ..config import get_config_loader
from ..infrastructure import MessageBus, StateStore
from ..l2d import Live2DService
from ..plugins import PluginBridge, PluginManager


@dataclass
class AppServices:
    """Runtime service graph for the API process."""

    message_bus: MessageBus
    state_store: StateStore
    plugin_manager: PluginManager
    plugin_bridge: PluginBridge
    live2d: Live2DService
    memory_engine: MemoryEngine
    memory_events: MemoryEventHandler
    emotion_manager: EmotionConfigManager
    emotion_analyzer: EmotionAnalyzer
    emotion_state: EmotionStateMachine
    personality: PersonalityModel
    dialogue_engine: DialogueEngine


async def build_services() -> AppServices:
    """Create and wire core services."""
    message_bus = MessageBus()
    await message_bus.start()

    state_store = StateStore()

    personality = PersonalityModel.create_default()

    memory_engine = MemoryEngine(config=load_memory_config(), bus=message_bus)
    await memory_engine.prepare()
    memory_events = MemoryEventHandler(memory_engine, message_bus)
    memory_events.attach()

    emotion_manager = EmotionConfigManager(bus=message_bus)
    emotion_analyzer = EmotionAnalyzer(manager=emotion_manager)
    emotion_state = EmotionStateMachine()

    plugin_manager = PluginManager(_resolve_plugins_dir())
    await _load_plugins(plugin_manager)
    plugin_bridge = PluginBridge(plugin_manager)
    await plugin_bridge.register_plugin_abilities()

    live2d = Live2DService(bus=message_bus)
    live2d.attach()

    dialogue_engine = DialogueEngine(
        default_provider="openai",
        default_model="gpt-4o",
        system_prompt=personality.generate_system_prompt(),
        message_bus=message_bus,
        memory_engine=memory_engine,
        provider_registry=ProviderRegistry,
        ability_registry=AbilityRegistry,
    )

    return AppServices(
        message_bus=message_bus,
        state_store=state_store,
        plugin_manager=plugin_manager,
        plugin_bridge=plugin_bridge,
        live2d=live2d,
        memory_engine=memory_engine,
        memory_events=memory_events,
        emotion_manager=emotion_manager,
        emotion_analyzer=emotion_analyzer,
        emotion_state=emotion_state,
        personality=personality,
        dialogue_engine=dialogue_engine,
    )


async def shutdown_services(services: AppServices) -> None:
    """Shutdown services in reverse order."""
    await services.plugin_manager.unload_all()
    await services.message_bus.stop()


def _resolve_plugins_dir() -> Path:
    loader = get_config_loader()
    for base in Path(__file__).resolve().parents:
        repo_plugins = base / "plugins"
        if repo_plugins.exists():
            return repo_plugins
    return loader.get_plugins_dir()


async def _load_plugins(plugin_manager: PluginManager) -> None:
    loader = get_config_loader()
    app_config = loader.get_app_config()

    if not app_config.plugins.enabled or not app_config.plugins.auto_start:
        return

    registry = loader.get_plugins_registry()
    enabled = [plugin.name for plugin in registry.plugins if plugin.enabled]
    if enabled:
        for plugin_name in enabled:
            await plugin_manager.load(plugin_name)
        return

    # Fallback for local development
    if (plugin_manager.plugins_dir / "vts-driver").exists():
        await plugin_manager.load("vts-driver")
