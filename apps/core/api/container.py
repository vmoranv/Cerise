"""
Service container wiring for the API layer.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from ..abilities import AbilityRegistry, CapabilityScheduler
from ..abilities.mcp_manager import McpManager
from ..ai import DialogueEngine, EmotionAnalyzer
from ..ai.agents import AgentService
from ..ai.dialogue import ProactiveChatService, load_proactive_config
from ..ai.emotion import EmotionConfigManager
from ..ai.memory import MemoryContextBuilder, MemoryEngine, MemoryPipeline, build_memory_extractor, load_memory_config
from ..ai.memory.layer_store import (
    build_core_profile_store,
    build_procedural_habits_store,
    build_semantic_facts_store,
)
from ..ai.providers import ProviderRegistry
from ..ai.skills import SkillService
from ..character import EmotionStateMachine, PersonalityModel
from ..config import get_config_loader
from ..events import Live2DEmotionHandler, MemoryEventHandler, MemoryLayerEventHandler
from ..infrastructure import EventBus, StateStore, set_default_bus
from ..infrastructure.mcp import McpServerConfig
from ..l2d import Live2DService
from ..operation import OperationService
from ..plugins import PluginBridge, PluginManager
from ..runtime import build_event_bus
from ..services import (
    CoreProfileService,
    EmotionService,
    Live2DDriver,
    LocalCoreProfileService,
    LocalEmotionService,
    LocalLive2DService,
    LocalMemoryService,
    LocalProceduralHabitsService,
    LocalSemanticFactsService,
    MemoryService,
    ProceduralHabitsService,
    SemanticFactsService,
)

logger = logging.getLogger(__name__)


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
    core_profiles: CoreProfileService
    semantic_facts: SemanticFactsService
    procedural_habits: ProceduralHabitsService
    memory_layer_events: MemoryLayerEventHandler
    memory_pipeline: MemoryPipeline
    live2d_events: Live2DEmotionHandler
    emotion_manager: EmotionConfigManager
    emotion_service: EmotionService
    emotion_state: EmotionStateMachine
    personality: PersonalityModel
    dialogue_engine: DialogueEngine
    proactive_chat: ProactiveChatService | None = None
    operation: OperationService | None = None
    agents: AgentService | None = None
    skills: SkillService | None = None
    mcp: McpManager | None = None


async def build_services() -> AppServices:
    """Create and wire core services."""
    loader = get_config_loader()
    app_config = loader.get_app_config()
    message_bus = build_event_bus(app_config.bus)
    await message_bus.start()
    set_default_bus(message_bus)

    state_store = StateStore()

    personality = PersonalityModel.create_default()

    emotion_manager = EmotionConfigManager(bus=message_bus)
    emotion_analyzer = EmotionAnalyzer(manager=emotion_manager)
    emotion_service = LocalEmotionService(emotion_analyzer)
    emotion_state = EmotionStateMachine(bus=message_bus)

    memory_config = load_memory_config()
    memory_engine = MemoryEngine(config=memory_config, bus=message_bus)
    await memory_engine.prepare()

    core_profile_store = build_core_profile_store(memory_config.l1_core)
    semantic_facts_store = build_semantic_facts_store(memory_config.l2_semantic)
    procedural_habits_store = build_procedural_habits_store(memory_config.l4_procedural)
    core_profiles = LocalCoreProfileService(core_profile_store)
    semantic_facts = LocalSemanticFactsService(semantic_facts_store)
    procedural_habits = LocalProceduralHabitsService(procedural_habits_store)
    memory_layer_events = MemoryLayerEventHandler(
        message_bus,
        core_profiles,
        semantic_facts,
        procedural_habits,
    )
    memory_layer_events.attach()

    context_builder = MemoryContextBuilder(
        config=memory_config.context,
        core_profiles=core_profiles,
        facts=semantic_facts,
        habits=procedural_habits,
    )

    memory_service = LocalMemoryService(memory_engine, context_builder=context_builder)
    memory_events = MemoryEventHandler(
        message_bus,
        memory_service,
        emotion=emotion_service,
        enable_emotion_snapshot=memory_config.pipeline.emotion_on_ingest,
    )
    memory_events.attach()

    memory_extractor = build_memory_extractor(memory_config)
    memory_pipeline = MemoryPipeline(bus=message_bus, store=memory_engine.store, extractor=memory_extractor)
    memory_pipeline.attach()

    plugin_manager = PluginManager(_resolve_plugins_dir())
    await _load_plugins(plugin_manager)
    plugin_bridge = PluginBridge(plugin_manager)
    await plugin_bridge.register_plugin_abilities()

    # MCP servers (optional): register MCP tools as abilities.
    mcp_servers: list[McpServerConfig] = []
    for entry in loader.get_mcp_config().servers:
        if not entry.enabled:
            continue
        if entry.transport and entry.transport != "stdio":
            logger.warning("Unsupported MCP transport '%s' for server '%s'", entry.transport, entry.id)
            continue
        if not entry.command:
            logger.warning("MCP server '%s' missing command, skipping", entry.id)
            continue

        merged_env = None
        if entry.env:
            merged_env = os.environ.copy()
            merged_env.update(entry.env)

        mcp_servers.append(
            McpServerConfig(
                id=entry.id,
                command=entry.command,
                args=entry.args,
                env=merged_env,
                enabled=entry.enabled,
                tool_name_prefix=entry.tool_name_prefix or None,
            ),
        )
    mcp = McpManager(servers=mcp_servers)
    await mcp.load_and_register(registry=AbilityRegistry)

    live2d_service = Live2DService()
    live2d = LocalLive2DService(live2d_service)
    live2d_events = Live2DEmotionHandler(bus=message_bus, live2d=live2d)
    live2d_events.attach()

    star_registry = loader.get_star_registry()
    capability_scheduler = CapabilityScheduler(
        registry=AbilityRegistry,
        config=app_config.capabilities,
        star_registry=star_registry,
        owner_provider=plugin_manager,
    )

    skills = SkillService(store=state_store)

    dialogue_engine = DialogueEngine(
        default_provider=app_config.ai.default_provider,
        default_model=app_config.ai.default_model,
        default_temperature=app_config.ai.temperature,
        default_top_p=app_config.ai.top_p,
        default_max_tokens=app_config.ai.max_tokens,
        system_prompt=personality.generate_system_prompt(),
        message_bus=message_bus,
        memory_service=memory_service,
        provider_registry=ProviderRegistry,
        ability_registry=capability_scheduler,
        skill_service=skills,
        skill_recall=False,
    )

    proactive_config = load_proactive_config()
    proactive_chat = ProactiveChatService(
        bus=message_bus,
        dialogue_engine=dialogue_engine,
        config=proactive_config,
    )
    proactive_chat.attach()
    await proactive_chat.start()

    agents = AgentService(store=state_store, bus=message_bus, dialogue_engine=dialogue_engine)

    return AppServices(
        message_bus=message_bus,
        state_store=state_store,
        plugin_manager=plugin_manager,
        plugin_bridge=plugin_bridge,
        live2d=live2d,
        memory_engine=memory_engine,
        memory_service=memory_service,
        memory_events=memory_events,
        core_profiles=core_profiles,
        semantic_facts=semantic_facts,
        procedural_habits=procedural_habits,
        memory_layer_events=memory_layer_events,
        memory_pipeline=memory_pipeline,
        live2d_events=live2d_events,
        emotion_manager=emotion_manager,
        emotion_service=emotion_service,
        emotion_state=emotion_state,
        personality=personality,
        dialogue_engine=dialogue_engine,
        proactive_chat=proactive_chat,
        operation=OperationService(bus=message_bus),
        agents=agents,
        skills=skills,
        mcp=mcp,
    )


async def shutdown_services(services: AppServices) -> None:
    """Shutdown services in reverse order."""
    if services.operation is not None:
        services.operation.close()
    if services.proactive_chat is not None:
        await services.proactive_chat.shutdown()
    if services.mcp is not None:
        await services.mcp.close()
    await services.plugin_manager.unload_all()
    await services.message_bus.stop()


def _resolve_plugins_dir() -> Path:
    loader = get_config_loader()
    for base in Path(__file__).resolve().parents:
        repo_plugins = base / "plugins"
        if not repo_plugins.exists() or not repo_plugins.is_dir():
            continue

        # We have two different "plugins" directories in the repo:
        # - repo-root/plugins (runtime plugin workspace; contains plugin folders with manifest.json)
        # - apps/core/plugins (Python package implementing the plugin system; no manifest.json children)
        # Prefer the runtime workspace by checking for child manifest.json files.
        try:
            has_manifest_child = any(
                child.is_dir() and not child.name.startswith("_") and (child / "manifest.json").exists()
                for child in repo_plugins.iterdir()
            )
        except Exception:
            has_manifest_child = False

        if has_manifest_child:
            return repo_plugins
    return loader.get_plugins_dir()


async def _load_plugins(plugin_manager: PluginManager) -> None:
    loader = get_config_loader()
    app_config = loader.get_app_config()

    if not app_config.plugins.enabled or not app_config.plugins.auto_start:
        return

    registry = loader.get_plugins_registry()
    star_registry = loader.get_star_registry()
    enabled = [plugin.name for plugin in registry.plugins if plugin.enabled]

    if enabled:
        for plugin_name in enabled:
            entry = star_registry.get_star(plugin_name) if star_registry else None
            if entry and not entry.enabled:
                continue
            plugin_dir = plugin_manager.plugins_dir / plugin_name
            schema = loader.load_star_schema(plugin_dir) if plugin_dir.exists() else None
            config = loader.load_star_config(plugin_name, schema=schema)
            await plugin_manager.load(plugin_name, config)
        return

    # Fallback for local development
    fallback_dir = plugin_manager.plugins_dir / "vts-driver"
    if fallback_dir.exists():
        schema = loader.load_star_schema(fallback_dir)
        config = loader.load_star_config("vts-driver", schema=schema)
        await plugin_manager.load("vts-driver", config)
