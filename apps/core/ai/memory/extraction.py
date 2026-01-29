"""Memory extraction helpers."""

from __future__ import annotations

import logging

from .config import MemoryConfig
from .extraction_types import (
    CoreProfileUpdate,
    MemoryExtraction,
    MemoryExtractor,
    ProceduralHabitUpdate,
    SemanticFactUpdate,
)
from .extractor_composite import CompositeMemoryExtractor
from .extractor_llm import LLMMemoryExtractor
from .extractor_rule import RuleBasedMemoryExtractor

logger = logging.getLogger(__name__)


def build_memory_extractor(config: MemoryConfig) -> MemoryExtractor:
    """Build extractor based on memory config."""
    extractor_type = (config.pipeline.extractor or "rule").lower()
    rule_extractor = RuleBasedMemoryExtractor()
    if extractor_type == "rule":
        return rule_extractor

    llm_provider = config.pipeline.llm_provider_id
    if extractor_type == "llm":
        if not llm_provider:
            logger.warning("LLM extractor selected without provider_id; using rule extractor")
            return rule_extractor
        return LLMMemoryExtractor(
            provider_id=llm_provider,
            model=config.pipeline.llm_model or None,
            temperature=config.pipeline.llm_temperature,
            max_tokens=config.pipeline.llm_max_tokens,
            task_type_mapping=config.pipeline.task_type_mapping,
        )

    if extractor_type == "composite":
        extractors: list[MemoryExtractor] = [rule_extractor]
        if llm_provider:
            extractors.append(
                LLMMemoryExtractor(
                    provider_id=llm_provider,
                    model=config.pipeline.llm_model or None,
                    temperature=config.pipeline.llm_temperature,
                    max_tokens=config.pipeline.llm_max_tokens,
                    task_type_mapping=config.pipeline.task_type_mapping,
                )
            )
        return CompositeMemoryExtractor(extractors)

    logger.warning("Unknown extractor '%s'; using rule extractor", extractor_type)
    return rule_extractor


__all__ = [
    "CoreProfileUpdate",
    "SemanticFactUpdate",
    "ProceduralHabitUpdate",
    "MemoryExtraction",
    "MemoryExtractor",
    "RuleBasedMemoryExtractor",
    "LLMMemoryExtractor",
    "CompositeMemoryExtractor",
    "build_memory_extractor",
]
