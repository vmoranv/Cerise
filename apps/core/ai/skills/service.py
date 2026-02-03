"""Skill library service (search + injection helper)."""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from ...infrastructure import StateStore
from .models import Skill, ToolRun
from .store import SkillStore, ToolRunStore


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
    return {t for t in tokens if t}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class SkillService:
    def __init__(self, *, store: StateStore, embedding_provider=None, embedding_model: str | None = None) -> None:
        self._store = SkillStore(store)
        self._tool_runs = ToolRunStore(store)
        self._embedding_provider = embedding_provider
        self._embedding_model = embedding_model

    async def upsert(
        self,
        *,
        skill_id: str | None = None,
        name: str,
        description: str = "",
        code: str = "",
        tags: list[str] | None = None,
    ) -> Skill:
        now = datetime.now()
        resolved_id = skill_id or str(uuid4())
        existing = await self._store.get_skill(resolved_id)
        created_at = existing.created_at if existing else now
        skill = Skill(
            id=resolved_id,
            name=name,
            description=description,
            code=code,
            tags=list(tags or []),
            created_at=created_at,
            updated_at=now,
        )
        await self._store.upsert_skill(skill)
        return skill

    async def list(self) -> list[Skill]:
        return await self._store.list_skills()

    async def get(self, skill_id: str) -> Skill | None:
        return await self._store.get_skill(skill_id)

    async def delete(self, skill_id: str) -> bool:
        return await self._store.delete_skill(skill_id)

    async def record_tool_run(
        self,
        *,
        session_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        success: bool,
        provider: str = "",
        model: str = "",
        tool_call_id: str | None = None,
        output: str = "",
        error: str | None = None,
    ) -> ToolRun:
        run = ToolRun(
            id=str(uuid4()),
            session_id=session_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            arguments=dict(arguments),
            provider=provider,
            model=model,
            success=bool(success),
            output=str(output or ""),
            error=error,
        )
        await self._tool_runs.append(session_id, run)
        return run

    async def list_tool_runs(self, session_id: str, *, limit: int | None = None) -> list[ToolRun]:
        return await self._tool_runs.list(session_id, limit=limit)

    async def clear_tool_runs(self, session_id: str) -> None:
        await self._tool_runs.clear(session_id)

    async def search(self, query: str, *, top_k: int = 3) -> list[Skill]:
        skills = await self._store.list_skills()
        if not skills or not query:
            return []
        top_k = max(1, int(top_k))

        # Prefer embeddings when available; fallback to token overlap.
        if self._embedding_provider is not None:
            try:
                vectors = await self._embedding_provider.embed(
                    [query] + [self._skill_text(s) for s in skills],
                    model=self._embedding_model,
                )
                query_vec = vectors[0]
                scored = [(skill, _cosine(query_vec, vec)) for skill, vec in zip(skills, vectors[1:])]
                scored.sort(key=lambda item: item[1], reverse=True)
                return [skill for skill, score in scored[:top_k] if score > 0]
            except Exception:
                pass

        q_tokens = _tokenize(query)
        scored = [(skill, _jaccard(q_tokens, _tokenize(self._skill_text(skill)))) for skill in skills]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [skill for skill, score in scored[:top_k] if score > 0]

    @staticmethod
    def _skill_text(skill: Skill) -> str:
        parts = [skill.name, skill.description, skill.code]
        return "\n".join(p for p in parts if p).strip()

    @staticmethod
    def build_injection_block(skills: list[Skill]) -> str:
        if not skills:
            return ""
        lines: list[str] = ["[Skill Library]"]
        for skill in skills:
            header = f"- {skill.name}"
            if skill.description:
                header += f": {skill.description}"
            lines.append(header)
            if skill.code:
                lines.append("```")
                lines.append(skill.code.strip())
                lines.append("```")
        lines.append("[/Skill Library]")
        return "\n".join(lines).strip()
