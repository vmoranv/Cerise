"""LLM-based memory extractor."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..providers import ChatOptions, Message, ProviderRegistry
from .extraction_types import (
    CoreProfileUpdate,
    MemoryExtraction,
    ProceduralHabitUpdate,
    SemanticFactUpdate,
)
from .types import MemoryRecord

logger = logging.getLogger(__name__)

_LLM_SYSTEM_PROMPT = "You are a memory extraction assistant. Return strict JSON only, without commentary."


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
