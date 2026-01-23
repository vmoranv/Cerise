"""Memory context builder for multi-layer recall."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .config import MemoryContextConfig
from .types import MemoryRecord, MemoryResult


class CoreProfileProvider(Protocol):
    async def list_profiles(self, session_id: str | None = None) -> list:
        """List core profiles."""


class SemanticFactsProvider(Protocol):
    async def list_facts(self, *, session_id: str | None = None, subject: str | None = None) -> list:
        """List semantic facts."""


class ProceduralHabitsProvider(Protocol):
    async def list_habits(self, *, session_id: str | None = None, task_type: str | None = None) -> list:
        """List procedural habits."""


@dataclass
class MemoryContextBuilder:
    """Build formatted memory context with layered weighting."""

    config: MemoryContextConfig
    core_profiles: CoreProfileProvider | None = None
    facts: SemanticFactsProvider | None = None
    habits: ProceduralHabitsProvider | None = None

    async def build(self, results: list[MemoryResult], session_id: str | None) -> str:
        if not self.config.enabled:
            return ""
        sections: list[str] = []
        quotas = self._allocate_quotas()

        core_quota = quotas.get("core", 0)
        if core_quota > 0 and self.core_profiles and session_id:
            profiles = await self.core_profiles.list_profiles(session_id=session_id)
            if profiles:
                sections.append(self._format_core_profiles(profiles[:core_quota]))

        fact_quota = quotas.get("semantic", 0)
        if fact_quota > 0 and self.facts and session_id:
            facts = await self.facts.list_facts(session_id=session_id)
            if facts:
                sections.append(self._format_facts(facts[:fact_quota]))

        habit_quota = quotas.get("procedural", 0)
        if habit_quota > 0 and self.habits and session_id:
            habits = await self.habits.list_habits(session_id=session_id)
            if habits:
                sections.append(self._format_habits(habits[:habit_quota]))

        episodic_quota = quotas.get("episodic", 0)
        if episodic_quota > 0 and results:
            trimmed = results[:episodic_quota]
            sections.append(self._format_results(trimmed))

        return "\n\n".join(section for section in sections if section)

    def _allocate_quotas(self) -> dict[str, int]:
        weights = self.config.layer_weights or {}
        total_weight = sum(weight for weight in weights.values() if weight > 0)
        if total_weight <= 0:
            return {}

        max_items = max(self.config.max_items, 0)
        quotas: dict[str, int] = {}
        remainder = max_items

        for layer, weight in weights.items():
            if weight <= 0 or max_items <= 0:
                quotas[layer] = 0
                continue
            quota = int(max_items * weight / total_weight)
            quotas[layer] = quota
            remainder -= quota

        if remainder > 0:
            ordered = sorted(weights.items(), key=lambda item: item[1], reverse=True)
            for layer, _ in ordered:
                if remainder <= 0:
                    break
                quotas[layer] = quotas.get(layer, 0) + 1
                remainder -= 1

        for layer, limit in self.config.max_per_layer.items():
            if layer in quotas:
                quotas[layer] = min(quotas[layer], max(limit, 0))

        return quotas

    def _format_core_profiles(self, profiles: list) -> str:
        lines = ["[Core Profile]"]
        for profile in profiles:
            summary = getattr(profile, "summary", "")
            profile_id = getattr(profile, "profile_id", "")
            label = f"{profile_id}: " if profile_id else ""
            if summary:
                lines.append(f"- {label}{summary}")
        return "\n".join(lines)

    def _format_facts(self, facts: list) -> str:
        lines = ["[Facts]"]
        for fact in facts:
            subject = getattr(fact, "subject", "")
            predicate = getattr(fact, "predicate", "")
            obj = getattr(fact, "object", "")
            if subject and predicate and obj:
                lines.append(f"- {subject} {predicate} {obj}")
        return "\n".join(lines)

    def _format_habits(self, habits: list) -> str:
        lines = ["[Habits]"]
        for habit in habits:
            task_type = getattr(habit, "task_type", "")
            instruction = getattr(habit, "instruction", "")
            if task_type and instruction:
                lines.append(f"- {task_type}: {instruction}")
        return "\n".join(lines)

    def _format_results(self, results: list[MemoryResult]) -> str:
        lines = ["[Episodic Recall]"]
        for idx, item in enumerate(results, start=1):
            record = item.record
            content = " ".join(record.content.split())
            if len(content) > 200:
                content = content[:197].rstrip() + "..."
            timestamp = record.created_at.strftime("%Y-%m-%d %H:%M")
            suffix = self._format_record_suffix(record, item.score)
            lines.append(f"{idx}. ({record.role} @ {timestamp}) {content}{suffix}")
        return "\n".join(lines)

    def _format_record_suffix(self, record: MemoryRecord, score: float) -> str:
        parts: list[str] = []
        if self.config.include_category and record.category:
            parts.append(f"category={record.category}")
        if self.config.include_tags and record.tags:
            parts.append("tags=" + ",".join(record.tags))
        if self.config.include_emotion and record.emotion:
            emotion_str = self._format_emotion(record.emotion)
            if emotion_str:
                parts.append(f"emotion={emotion_str}")
        if self.config.include_scores:
            parts.append(f"score={score:.2f}")
        if not parts:
            return ""
        return " [" + " | ".join(parts) + "]"

    def _format_emotion(self, emotion: dict[str, float]) -> str:
        values: list[str] = []
        for key in ("valence", "arousal", "dominance", "intensity", "confidence"):
            if key in emotion:
                values.append(f"{key}:{emotion[key]:.2f}")
        return ",".join(values)
