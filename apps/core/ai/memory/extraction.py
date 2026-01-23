"""Memory extraction helpers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..providers import ChatOptions, Message, ProviderRegistry
from .config import MemoryConfig
from .types import MemoryRecord

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CoreProfileUpdate:
    """Core profile update extracted from a message."""

    summary: str
    profile_id: str | None = None
    session_id: str | None = None


@dataclass(slots=True)
class SemanticFactUpdate:
    """Semantic fact extracted from a message."""

    subject: str
    predicate: str
    object: str
    fact_id: str | None = None
    session_id: str | None = None


@dataclass(slots=True)
class ProceduralHabitUpdate:
    """Procedural habit extracted from a message."""

    task_type: str
    instruction: str
    habit_id: str | None = None
    session_id: str | None = None


@dataclass(slots=True)
class MemoryExtraction:
    """Collection of extracted memory updates."""

    core_updates: list[CoreProfileUpdate] = field(default_factory=list)
    facts: list[SemanticFactUpdate] = field(default_factory=list)
    habits: list[ProceduralHabitUpdate] = field(default_factory=list)


class MemoryExtractor(Protocol):
    """Extractor interface for memory pipeline."""

    async def extract(self, *, record: MemoryRecord) -> MemoryExtraction:
        """Extract structured memory updates from a record."""


class RuleBasedMemoryExtractor:
    """Extract memory updates from metadata or inline hints."""

    def __init__(self, *, allow_metadata: bool = True, allow_inline: bool = True) -> None:
        self._allow_metadata = allow_metadata
        self._allow_inline = allow_inline

    async def extract(self, *, record: MemoryRecord) -> MemoryExtraction:
        extraction = MemoryExtraction()
        if self._allow_metadata:
            self._extract_metadata(record, extraction)
        if self._allow_inline:
            self._extract_inline(record, extraction)
        return extraction

    def _extract_metadata(self, record: MemoryRecord, extraction: MemoryExtraction) -> None:
        metadata = record.metadata or {}
        core_updates = self._ensure_list(metadata.get("core_updates") or metadata.get("core_update"))
        if not core_updates and isinstance(metadata.get("core_summary"), str):
            core_updates = [metadata["core_summary"]]
        for update in core_updates:
            core_entry = self._parse_core_update(update, record)
            if core_entry:
                extraction.core_updates.append(core_entry)

        facts = self._ensure_list(metadata.get("facts") or metadata.get("new_facts"))
        for fact in facts:
            fact_entry = self._parse_fact_update(fact, record)
            if fact_entry:
                extraction.facts.append(fact_entry)

        habits = self._ensure_list(metadata.get("habits") or metadata.get("new_habits"))
        for habit in habits:
            habit_entry = self._parse_habit_update(habit, record)
            if habit_entry:
                extraction.habits.append(habit_entry)

    def _extract_inline(self, record: MemoryRecord, extraction: MemoryExtraction) -> None:
        for line in record.content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if lower.startswith("core:"):
                payload = stripped[5:].strip()
                core_entry = self._parse_inline_core(payload, record)
                if core_entry:
                    extraction.core_updates.append(core_entry)
                continue
            if lower.startswith("fact:"):
                payload = stripped[5:].strip()
                fact_entry = self._parse_inline_fact(payload, record)
                if fact_entry:
                    extraction.facts.append(fact_entry)
                continue
            if lower.startswith("habit:"):
                payload = stripped[6:].strip()
                habit_entry = self._parse_inline_habit(payload, record)
                if habit_entry:
                    extraction.habits.append(habit_entry)

    def _parse_core_update(self, update: Any, record: MemoryRecord) -> CoreProfileUpdate | None:
        if isinstance(update, str):
            summary = update.strip()
            if summary:
                return CoreProfileUpdate(summary=summary, session_id=record.session_id)
            return None
        if not isinstance(update, dict):
            return None
        summary = update.get("summary")
        if not summary:
            summary = self._build_core_summary(update)
        if not summary:
            return None
        return CoreProfileUpdate(
            summary=str(summary),
            profile_id=update.get("profile_id"),
            session_id=update.get("session_id") or record.session_id,
        )

    def _parse_fact_update(self, fact: Any, record: MemoryRecord) -> SemanticFactUpdate | None:
        if not isinstance(fact, dict):
            return None
        subject = fact.get("subject") or fact.get("entity")
        predicate = fact.get("predicate") or fact.get("attribute")
        object_value = fact.get("object") or fact.get("value")
        if not (subject and predicate and object_value):
            return None
        return SemanticFactUpdate(
            subject=str(subject),
            predicate=str(predicate),
            object=str(object_value),
            fact_id=fact.get("fact_id"),
            session_id=fact.get("session_id") or record.session_id,
        )

    def _parse_habit_update(self, habit: Any, record: MemoryRecord) -> ProceduralHabitUpdate | None:
        if not isinstance(habit, dict):
            return None
        task_type = habit.get("task_type") or habit.get("type")
        instruction = habit.get("instruction") or habit.get("rule")
        if not (task_type and instruction):
            return None
        return ProceduralHabitUpdate(
            task_type=str(task_type),
            instruction=str(instruction),
            habit_id=habit.get("habit_id"),
            session_id=habit.get("session_id") or record.session_id,
        )

    def _parse_inline_core(self, payload: str, record: MemoryRecord) -> CoreProfileUpdate | None:
        if not payload:
            return None
        if "|" in payload:
            parts = [part.strip() for part in payload.split("|", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                return CoreProfileUpdate(summary=parts[1], profile_id=parts[0], session_id=record.session_id)
        return CoreProfileUpdate(summary=payload, session_id=record.session_id)

    def _parse_inline_fact(self, payload: str, record: MemoryRecord) -> SemanticFactUpdate | None:
        parts = [part.strip() for part in payload.split("|")]
        if len(parts) >= 3:
            return SemanticFactUpdate(
                subject=parts[0],
                predicate=parts[1],
                object="|".join(parts[2:]),
                session_id=record.session_id,
            )
        return None

    def _parse_inline_habit(self, payload: str, record: MemoryRecord) -> ProceduralHabitUpdate | None:
        parts = [part.strip() for part in payload.split("|", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            return ProceduralHabitUpdate(
                task_type=parts[0],
                instruction=parts[1],
                session_id=record.session_id,
            )
        return None

    def _ensure_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _build_core_summary(self, update: dict) -> str | None:
        value = update.get("value") or update.get("content")
        field = update.get("field")
        target = update.get("target")
        label_parts = [part for part in (target, field) if part]
        if value is None:
            return None
        prefix = ".".join(str(part) for part in label_parts)
        if prefix:
            return f"{prefix}: {value}"
        return str(value)


class LLMMemoryExtractor:
    """Use an LLM provider to extract structured memory updates."""

    def __init__(
        self,
        *,
        provider_id: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 800,
        task_type_mapping: dict[str, str] | None = None,
    ) -> None:
        self._provider_id = provider_id
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._task_type_mapping = task_type_mapping or {}

    async def extract(self, *, record: MemoryRecord) -> MemoryExtraction:
        provider = ProviderRegistry.get(self._provider_id)
        if not provider:
            logger.warning("LLM extractor provider '%s' not found", self._provider_id)
            return MemoryExtraction()
        prompt = self._build_prompt(record)
        options = ChatOptions(
            model=self._model or provider.available_models[0],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        try:
            response = await provider.chat(
                [
                    Message(role="system", content=_LLM_SYSTEM_PROMPT),
                    Message(role="user", content=prompt),
                ],
                options,
            )
        except Exception:
            logger.exception("LLM extraction failed")
            return MemoryExtraction()
        return self._parse_response(response.content, record)

    def _build_prompt(self, record: MemoryRecord) -> str:
        metadata = record.metadata or {}
        return (
            "Extract core profile updates, semantic facts, and procedural habits from the message.\n"
            "Return JSON with keys: core_updates, facts, habits.\n"
            "core_updates: list of {summary, profile_id?}\n"
            "facts: list of {subject, predicate, object}\n"
            "habits: list of {task_type, instruction}\n"
            "If nothing, return empty lists. Output JSON only.\n\n"
            f"Session: {record.session_id}\nRole: {record.role}\n"
            f"Metadata: {json.dumps(metadata, ensure_ascii=False)}\n"
            f"Message:\n{record.content}\n"
        )

    def _parse_response(self, content: str, record: MemoryRecord) -> MemoryExtraction:
        payload = _safe_json(content)
        if not isinstance(payload, dict):
            return MemoryExtraction()
        extraction = MemoryExtraction()

        for update in payload.get("core_updates", []) or []:
            core_entry = self._parse_core_update(update, record)
            if core_entry:
                extraction.core_updates.append(core_entry)

        for fact in payload.get("facts", []) or []:
            fact_entry = self._parse_fact_update(fact, record)
            if fact_entry:
                extraction.facts.append(fact_entry)

        for habit in payload.get("habits", []) or []:
            habit_entry = self._parse_habit_update(habit, record)
            if habit_entry:
                extraction.habits.append(habit_entry)

        return extraction

    def _parse_core_update(self, update: Any, record: MemoryRecord) -> CoreProfileUpdate | None:
        if isinstance(update, str):
            summary = update.strip()
            if summary:
                return CoreProfileUpdate(summary=summary, session_id=record.session_id)
            return None
        if not isinstance(update, dict):
            return None
        summary = update.get("summary")
        if not summary:
            return None
        return CoreProfileUpdate(
            summary=str(summary),
            profile_id=update.get("profile_id"),
            session_id=update.get("session_id") or record.session_id,
        )

    def _parse_fact_update(self, fact: Any, record: MemoryRecord) -> SemanticFactUpdate | None:
        if not isinstance(fact, dict):
            return None
        subject = fact.get("subject") or fact.get("entity")
        predicate = fact.get("predicate") or fact.get("attribute")
        object_value = fact.get("object") or fact.get("value")
        if not (subject and predicate and object_value):
            return None
        return SemanticFactUpdate(
            subject=str(subject),
            predicate=str(predicate),
            object=str(object_value),
            fact_id=fact.get("fact_id"),
            session_id=fact.get("session_id") or record.session_id,
        )

    def _parse_habit_update(self, habit: Any, record: MemoryRecord) -> ProceduralHabitUpdate | None:
        if not isinstance(habit, dict):
            return None
        task_type = habit.get("task_type") or habit.get("type")
        instruction = habit.get("instruction") or habit.get("rule")
        if not (task_type and instruction):
            return None
        mapped_task = self._task_type_mapping.get(str(task_type), str(task_type))
        return ProceduralHabitUpdate(
            task_type=mapped_task,
            instruction=str(instruction),
            habit_id=habit.get("habit_id"),
            session_id=habit.get("session_id") or record.session_id,
        )


class CompositeMemoryExtractor:
    """Chain multiple extractors into one."""

    def __init__(self, extractors: list[MemoryExtractor]) -> None:
        self._extractors = [extractor for extractor in extractors if extractor]

    async def extract(self, *, record: MemoryRecord) -> MemoryExtraction:
        extraction = MemoryExtraction()
        for extractor in self._extractors:
            result = await extractor.extract(record=record)
            extraction.core_updates.extend(result.core_updates)
            extraction.facts.extend(result.facts)
            extraction.habits.extend(result.habits)
        return extraction


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


_LLM_SYSTEM_PROMPT = "You are a memory extraction assistant. Return strict JSON only, without commentary."


def _safe_json(content: str) -> Any:
    if not content:
        return None
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None
