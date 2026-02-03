"""Agent management routes (create/send/wakeup + SSE)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...ai.agents import AgentService
from ...infrastructure import Event, EventBus
from ..dependencies import get_agent_service, get_services

router = APIRouter()


class AgentCreateRequest(BaseModel):
    agent_id: str | None = None
    parent_id: str | None = None
    name: str = ""


class AgentMessageCreateRequest(BaseModel):
    role: str = "user"
    content: str


class AgentWakeupRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None


def _serialize_event(event: Event) -> dict[str, Any]:
    payload = event.to_dict()
    payload["data"] = payload.get("data") or {}
    return payload


@router.post("/agents")
async def create_agent(request: AgentCreateRequest, agents: AgentService = Depends(get_agent_service)) -> dict:
    agent = await agents.create(agent_id=request.agent_id, parent_id=request.parent_id, name=request.name)
    return agent.to_dict()


@router.get("/agents")
async def list_agents(agents: AgentService = Depends(get_agent_service)) -> dict:
    items = await agents.list_agents()
    return {"agents": [agent.to_dict() for agent in items]}


@router.post("/agents/{agent_id}/messages")
async def send_agent_message(
    agent_id: str,
    request: AgentMessageCreateRequest,
    agents: AgentService = Depends(get_agent_service),
) -> dict:
    if not request.content:
        raise HTTPException(status_code=400, detail="content is required")
    message = await agents.send(agent_id=agent_id, role=request.role, content=request.content)
    return message.to_dict()


@router.get("/agents/{agent_id}/messages")
async def list_agent_messages(
    agent_id: str, limit: int | None = None, agents: AgentService = Depends(get_agent_service)
) -> dict:
    messages = await agents.list_messages(agent_id, limit=limit)
    return {"messages": [msg.to_dict() for msg in messages]}


@router.post("/agents/{agent_id}/wakeup")
async def wakeup_agent(
    agent_id: str,
    request: AgentWakeupRequest,
    agents: AgentService = Depends(get_agent_service),
) -> dict:
    message = await agents.wakeup(
        agent_id=agent_id,
        provider=request.provider,
        model=request.model,
        temperature=request.temperature,
    )
    return {"message": message.to_dict() if message else None}


@router.get("/agents/{agent_id}/events")
async def stream_agent_events(agent_id: str, request: Request, services=Depends(get_services)) -> StreamingResponse:
    bus: EventBus = services.message_bus
    queue: asyncio.Queue[Event] = asyncio.Queue()

    async def handler(event: Event) -> None:
        data = event.data or {}
        if not isinstance(data, dict):
            return
        if data.get("agent_id") == agent_id:
            await queue.put(event)
            return
        if event.type.startswith("dialogue.") and data.get("session_id") == agent_id:
            await queue.put(event)

    bus.subscribe("agent.*", handler)
    bus.subscribe("dialogue.*", handler)

    async def event_stream():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except TimeoutError:
                    yield ": ping\n\n"
                    continue

                payload = json.dumps(_serialize_event(event), ensure_ascii=False)
                yield f"data: {payload}\n\n"
                queue.task_done()
        except asyncio.CancelledError:
            return
        finally:
            bus.unsubscribe("agent.*", handler)
            bus.unsubscribe("dialogue.*", handler)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
