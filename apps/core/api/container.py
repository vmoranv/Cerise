"""
Service container wiring for the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..abilities import AbilityRegistry
from ..ai import DialogueEngine, EmotionAnalyzer
from ..ai.emotion import EmotionConfigManager
from ..ai.memory import MemoryEngine, MemoryEventHandler, load_memory_config
from ..ai.providers import ProviderRegistry
from ..character import EmotionStateMachine, PersonalityModel
from ..infrastructure import MessageBus, StateStore


@dataclass
class AppServices:
    """Runtime service graph for the API process."""

    message_bus: MessageBus
    state_store: StateStore
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
    await services.message_bus.stop()
