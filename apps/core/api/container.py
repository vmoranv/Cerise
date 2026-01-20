"""
Service container wiring for the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..abilities import AbilityRegistry
from ..ai import DialogueEngine, EmotionAnalyzer
from ..ai.emotion import EmotionConfigManager
from ..ai.memory import MemoryEngine, load_memory_config
from ..ai.providers import ProviderRegistry
from ..character import EmotionStateMachine, PersonalityModel
from ..config import get_config_loader
from ..events import Live2DEmotionHandler, MemoryEventHandler
from ..infrastructure import EventBus, StateStore, set_default_bus
from ..l2d import Live2DService
from ..plugins import PluginBridge, PluginManager
from ..runtime import build_event_bus
from ..services import (
    EmotionService,
    Live2DDriver,
    LocalEmotionService,
    LocalLive2DService,
    LocalMemoryService,
    MemoryService,
)


@dataclass
class AppServices:
    """Runtime service graph for the API process."""

    message_bus: EventBus
    state_store: StateStore
    plugin_manager: PluginManager
    plugin_bridge: PluginBridge
    live2d: Live2DDriver
    memory_engine: MemoryEngine
    memory_service: MemoryService
    memory_events: MemoryEventHandler
    live2d_events: Live2DEmotionHandler
    emotion_manager: EmotionConfigManager
    emotion_service: EmotionService
    emotion_state: EmotionStateMachine
    personality: PersonalityModel
    dialogue_engine: DialogueEngine


async def build_services() -> AppServices:
    """Create and wire core services."""
    loader = get_config_loader()
    app_config = loader.get_app_config()
    message_bus = build_event_bus(app_config.bus)
    await message_bus.start()
    set_default_bus(message_bus)

    state_store = StateStore()

    personality = PersonalityModel.create_default()

    memory_engine = MemoryEngine(config=load_memory_config(), bus=message_bus)
    await memory_engine.prepare()
    memory_service = LocalMemoryService(memory_engine)
    memory_events = MemoryEventHandler(message_bus, memory_service)
    memory_events.attach()

    emotion_manager = EmotionConfigManager(bus=message_bus)
    emotion_analyzer = EmotionAnalyzer(manager=emotion_manager)
    emotion_service = LocalEmotionService(emotion_analyzer)
    emotion_state = EmotionStateMachine(bus=message_bus)

    plugin_manager = PluginManager(_resolve_plugins_dir())
    await _load_plugins(plugin_manager)
    plugin_bridge = PluginBridge(plugin_manager)
    await plugin_bridge.register_plugin_abilities()

    live2d_service = Live2DService()
    live2d = LocalLive2DService(live2d_service)
    live2d_events = Live2DEmotionHandler(bus=message_bus, live2d=live2d)
    live2d_events.attach()

    dialogue_engine = DialogueEngine(
        default_provider="openai",
        default_model="gpt-4o",
        system_prompt=personality.generate_system_prompt(),
        message_bus=message_bus,
        memory_service=memory_service,
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
        memory_service=memory_service,
        memory_events=memory_events,
        live2d_events=live2d_events,
        emotion_manager=emotion_manager,
        emotion_service=emotion_service,
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
