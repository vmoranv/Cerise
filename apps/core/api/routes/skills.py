"""Skill library routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...ai.skills import SkillService
from ..dependencies import get_skill_service

router = APIRouter()


class SkillUpsertRequest(BaseModel):
    id: str | None = None
    name: str
    description: str = ""
    code: str = ""
    tags: list[str] | None = None


class SkillSearchRequest(BaseModel):
    query: str
    top_k: int = 3


@router.get("/skills")
async def list_skills(skills: SkillService = Depends(get_skill_service)) -> dict:
    items = await skills.list()
    return {"skills": [s.to_dict() for s in items]}


@router.post("/skills")
async def upsert_skill(request: SkillUpsertRequest, skills: SkillService = Depends(get_skill_service)) -> dict:
    if not request.name:
        raise HTTPException(status_code=400, detail="name is required")
    skill = await skills.upsert(
        skill_id=request.id,
        name=request.name,
        description=request.description,
        code=request.code,
        tags=request.tags,
    )
    return skill.to_dict()


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str, skills: SkillService = Depends(get_skill_service)) -> dict:
    ok = await skills.delete(skill_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "deleted"}


@router.post("/skills/search")
async def search_skills(request: SkillSearchRequest, skills: SkillService = Depends(get_skill_service)) -> dict:
    results = await skills.search(request.query, top_k=request.top_k)
    return {"skills": [s.to_dict() for s in results]}
