"""Dependency providers for API routes."""

from __future__ import annotations

from typing import cast

from fastapi import Depends, HTTPException, Request

from ..ai import DialogueEngine
from ..ai.agents import AgentService
from ..ai.skills import SkillService
from ..character import EmotionStateMachine, PersonalityModel
from ..services.ports import EmotionService, Live2DDriver
from .container import AppServices


def get_services(request: Request) -> AppServices:
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(status_code=500, detail="Services not initialized")
    return cast(AppServices, services)


def get_dialogue_engine(services: AppServices = Depends(get_services)) -> DialogueEngine:
    return services.dialogue_engine


def get_emotion_service(services: AppServices = Depends(get_services)) -> EmotionService:
    return services.emotion_service


def get_emotion_state(services: AppServices = Depends(get_services)) -> EmotionStateMachine:
    return services.emotion_state


def get_personality(services: AppServices = Depends(get_services)) -> PersonalityModel:
    return services.personality


def get_live2d(services: AppServices = Depends(get_services)) -> Live2DDriver:
    return services.live2d


def get_agent_service(services: AppServices = Depends(get_services)) -> AgentService:
    if services.agents is None:
        raise HTTPException(status_code=500, detail="Agent service not initialized")
    return services.agents


def get_skill_service(services: AppServices = Depends(get_services)) -> SkillService:
    if services.skills is None:
        raise HTTPException(status_code=500, detail="Skill service not initialized")
    return services.skills
