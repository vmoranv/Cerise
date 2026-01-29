"""Rule-based memory extractor."""

from __future__ import annotations

from typing import Any

from .extraction_types import (
    CoreProfileUpdate,
    MemoryExtraction,
    ProceduralHabitUpdate,
    SemanticFactUpdate,
)
from .types import MemoryRecord


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
