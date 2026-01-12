"""
API Gateway

FastAPI application for REST and WebSocket endpoints.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..ai import DialogueEngine, EmotionAnalyzer
from ..ai.dialogue import Session
from ..character import EmotionStateMachine, PersonalityModel
from ..l2d import Live2DService
from .container import AppServices, build_services, shutdown_services

logger = logging.getLogger(__name__)

# API Router
router = APIRouter()


# Pydantic models for API
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    provider: str | None = None
    model: str | None = None
    temperature: float = 0.7
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    session_id: str
    emotion: str
    emotion_intensity: float


class SessionCreate(BaseModel):
    user_id: str = ""
    personality: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    message_count: int


class EmotionUpdate(BaseModel):
    emotion: str
    intensity: float = 1.0


class Live2DParameter(BaseModel):
    id: str
    value: float
    weight: float | None = None


class Live2DParametersUpdate(BaseModel):
    parameters: list[Live2DParameter]
    smoothing: float | None = None


class Live2DEmotionUpdate(BaseModel):
    valence: float
    arousal: float
    intensity: float
    smoothing: float | None = None


class HealthResponse(BaseModel):
    status: str
    version: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager"""
    logger.info("Starting Cerise API server...")
    app.state.services = await build_services()
    logger.info("Cerise API server started")

    yield

    logger.info("Shutting down Cerise API server...")
    services = getattr(app.state, "services", None)
    if services:
        await shutdown_services(services)
    logger.info("Cerise API server stopped")


def create_app() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="Cerise API",
        description="AI-driven Live2D Virtual Character API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


def get_services(request: Request) -> AppServices:
    services = getattr(request.app.state, "services", None)
    if not services:
        raise HTTPException(status_code=500, detail="Services not initialized")
    return services


def get_dialogue_engine(services: AppServices = Depends(get_services)) -> DialogueEngine:
    return services.dialogue_engine


def get_emotion_analyzer(services: AppServices = Depends(get_services)) -> EmotionAnalyzer:
    return services.emotion_analyzer


def get_emotion_state(services: AppServices = Depends(get_services)) -> EmotionStateMachine:
    return services.emotion_state


def get_personality(services: AppServices = Depends(get_services)) -> PersonalityModel:
    return services.personality


def get_live2d(services: AppServices = Depends(get_services)) -> Live2DService:
    return services.live2d


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="ok", version="0.1.0")


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreate,
    dialogue_engine: DialogueEngine = Depends(get_dialogue_engine),
    personality: PersonalityModel = Depends(get_personality),
):
    """Create a new conversation session"""
    system_prompt = personality.generate_system_prompt() if personality else ""

    session = dialogue_engine.create_session(
        user_id=request.user_id,
        system_prompt=system_prompt,
    )

    return SessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        message_count=len(session.messages),
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    dialogue_engine: DialogueEngine = Depends(get_dialogue_engine),
):
    """Get session info"""
    session = dialogue_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        message_count=len(session.messages),
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    dialogue_engine: DialogueEngine = Depends(get_dialogue_engine),
):
    """Delete a session"""
    if dialogue_engine.delete_session(session_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    dialogue_engine: DialogueEngine = Depends(get_dialogue_engine),
    emotion_analyzer: EmotionAnalyzer = Depends(get_emotion_analyzer),
    emotion_state: EmotionStateMachine = Depends(get_emotion_state),
):
    """Send a chat message"""
    session = None
    if request.session_id:
        session = dialogue_engine.get_session(request.session_id)

    if not session:
        session = dialogue_engine.create_session()

    try:
        # Get AI response
        response = await dialogue_engine.chat(
            session=session,
            user_message=request.message,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
        )

        # Analyze emotion
        emotion_result = emotion_analyzer.analyze(response)
        emotion_state.set_emotion(
            emotion_result.primary_emotion.value,
            intensity=emotion_result.confidence,
        )

        current_emotion = emotion_state.current_state.value
        current_intensity = emotion_state.current_intensity

        return ChatResponse(
            response=response,
            session_id=session.id,
            emotion=current_emotion,
            emotion_intensity=current_intensity,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/emotion")
async def get_emotion(emotion_state: EmotionStateMachine = Depends(get_emotion_state)):
    """Get current emotion state"""
    return emotion_state.get_animation_params()


@router.post("/emotion")
async def set_emotion(
    request: EmotionUpdate,
    emotion_state: EmotionStateMachine = Depends(get_emotion_state),
):
    """Manually set emotion state"""
    emotion_state.set_emotion(request.emotion, request.intensity)
    return emotion_state.get_animation_params()


@router.post("/l2d/emotion")
async def set_live2d_emotion(
    request: Live2DEmotionUpdate,
    live2d: Live2DService = Depends(get_live2d),
):
    """Manually set Live2D emotion parameters."""
    result = await live2d.set_emotion(
        valence=request.valence,
        arousal=request.arousal,
        intensity=request.intensity,
        smoothing=request.smoothing,
        user_id="manual",
        session_id="l2d",
    )
    if result is None:
        raise HTTPException(status_code=503, detail="Live2D ability not available")
    if not result.success:
        raise HTTPException(status_code=502, detail=result.error or "Live2D update failed")
    return {"status": "ok", "data": result.data}


@router.post("/l2d/params")
async def set_live2d_parameters(
    request: Live2DParametersUpdate,
    live2d: Live2DService = Depends(get_live2d),
):
    """Manually set arbitrary Live2D parameters."""
    result = await live2d.set_parameters(
        parameters=[param.model_dump(exclude_none=True) for param in request.parameters],
        smoothing=request.smoothing,
        user_id="manual",
        session_id="l2d",
    )
    if result is None:
        raise HTTPException(status_code=503, detail="Live2D ability not available")
    if not result.success:
        raise HTTPException(status_code=502, detail=result.error or "Live2D update failed")
    return {"status": "ok", "data": result.data}


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat"""
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    services = getattr(websocket.app.state, "services", None)
    if not services:
        await websocket.send_json({"type": "error", "message": "Services not initialized"})
        await websocket.close(code=1011)
        return

    dialogue_engine = services.dialogue_engine
    emotion_analyzer = services.emotion_analyzer
    emotion_state = services.emotion_state

    session: Session | None = None

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "chat")

            if action == "create_session":
                session = dialogue_engine.create_session()
                await websocket.send_json(
                    {
                        "type": "session_created",
                        "session_id": session.id,
                    }
                )

            elif action == "chat":
                message = data.get("message", "")
                if not message or not session:
                    await websocket.send_json({"type": "error", "message": "No message or session"})
                    continue

                # Stream response
                await websocket.send_json({"type": "start"})

                full_response = ""
                async for chunk in dialogue_engine.stream_chat(
                    session=session,
                    user_message=message,
                    provider=data.get("provider"),
                    model=data.get("model"),
                ):
                    full_response += chunk
                    await websocket.send_json({"type": "chunk", "content": chunk})

                # Analyze final emotion
                emotion_result = emotion_analyzer.analyze(full_response)
                emotion_state.set_emotion(
                    emotion_result.primary_emotion.value,
                    intensity=emotion_result.confidence,
                )

                await websocket.send_json(
                    {
                        "type": "end",
                        "emotion": emotion_state.current_state.value,
                    }
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# Main entry point
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
