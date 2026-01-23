"""
Memory compression utilities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from ..providers import ChatOptions, Message, ProviderRegistry
from .time_utils import now
from .types import MemoryRecord

logger = logging.getLogger(__name__)


class MemorySummaryProvider(Protocol):
    async def summarize(self, records: list[MemoryRecord], *, max_chars: int) -> str | None:
        """Summarize records into a short text."""


class ProviderSummaryProvider:
    """LLM-backed summary provider."""

    def __init__(
        self,
        *,
        provider_id: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> None:
        self._provider_id = provider_id
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def summarize(self, records: list[MemoryRecord], *, max_chars: int) -> str | None:
        provider = ProviderRegistry.get(self._provider_id)
        if not provider:
            logger.warning("Summary provider '%s' not found", self._provider_id)
            return None
        prompt = _build_summary_prompt(records)
        options = ChatOptions(
            model=self._model or provider.available_models[0],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        try:
            response = await provider.chat(
                [
                    Message(role="system", content=_SUMMARY_SYSTEM_PROMPT),
                    Message(role="user", content=prompt),
                ],
                options,
            )
        except Exception:
            logger.exception("Summary generation failed")
            return None
        summary = (response.content or "").strip()
        if not summary:
            return None
        if len(summary) > max_chars:
            summary = summary[:max_chars].rstrip() + "..."
        return summary


_SUMMARY_SYSTEM_PROMPT = "Summarize memory snippets into concise bullet points. Return plain text only."


def _build_summary_prompt(records: list[MemoryRecord]) -> str:
    lines: list[str] = []
    for record in records:
        content = " ".join(record.content.split())
        if len(content) > 200:
            content = content[:197].rstrip() + "..."
        lines.append(f"- [{record.role}] {content}")
    return "\n".join(lines)


@dataclass
class MemoryCompressor:
    """Compress older memories into a summary record."""

    threshold: int
    window: int
    max_chars: int
    summary_provider: MemorySummaryProvider | None = None

    def should_compress(self, record_count: int) -> bool:
        return self.threshold > 0 and record_count >= self.threshold

    def select_records(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        candidates = [
            record for record in records if not record.metadata.get("compressed") and not record.metadata.get("summary")
        ]
        if len(candidates) < self.window:
            return []
        return candidates[: self.window]

    async def compress_async(self, records: list[MemoryRecord]) -> MemoryRecord:
        if not records:
            raise ValueError("No records to compress")
        if self.summary_provider:
            summary = await self.summary_provider.summarize(records, max_chars=self.max_chars)
            if summary:
                return self._build_summary_record(records, summary, created_by="memory_compressor_llm")
        return self.compress(records)

    def _build_summary_record(
        self,
        records: list[MemoryRecord],
        summary: str,
        *,
        created_by: str,
    ) -> MemoryRecord:
        return MemoryRecord(
            session_id=records[0].session_id,
            role="system",
            content="Memory Summary:\n" + summary,
            metadata={
                "summary": True,
                "compressed": True,
                "source_ids": [record.id for record in records],
                "source_count": len(records),
                "source_last_at": max(record.created_at for record in records).isoformat(),
                "source_first_at": min(record.created_at for record in records).isoformat(),
                "created_by": created_by,
            },
            created_at=now(),
        )

    def compress(self, records: list[MemoryRecord]) -> MemoryRecord:
        if not records:
            raise ValueError("No records to compress")
        lines = []
        for record in records:
            content = " ".join(record.content.split())
            if len(content) > 160:
                content = content[:157].rstrip() + "..."
            lines.append(f"- [{record.role}] {content}")
        summary = "\n".join(lines)
        if len(summary) > self.max_chars:
            summary = summary[: self.max_chars].rstrip() + "..."

        return self._build_summary_record(records, summary, created_by="memory_compressor")
