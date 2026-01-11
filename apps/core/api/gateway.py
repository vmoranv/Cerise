"""
API Gateway

FastAPI application for REST and WebSocket endpoints.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..ai import DialogueEngine, EmotionAnalyzer
from ..ai.dialogue import Session
from ..character import EmotionStateMachine, PersonalityModel
from ..infrastructure import ConfigManager, MessageBus, StateStore

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


class HealthResponse(BaseModel):
    status: str
    version: str


# Global instances
dialogue_engine: DialogueEngine | None = None
emotion_analyzer: EmotionAnalyzer | None = None
emotion_state: EmotionStateMachine | None = None
personality: PersonalityModel | None = None
message_bus: MessageBus | None = None
state_store: StateStore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager"""
    global dialogue_engine, emotion_analyzer, emotion_state, personality, message_bus, state_store

    logger.info("Starting Cerise API server...")

    # Initialize components
    message_bus = MessageBus()
    await message_bus.start()

    state_store = StateStore()

    # Initialize config
    _config = ConfigManager()

    # Create default personality
    personality = PersonalityModel.create_default()

    # Initialize dialogue engine
    dialogue_engine = DialogueEngine(
        default_provider="openai",
        default_model="gpt-4o",
        system_prompt=personality.generate_system_prompt(),
    )

    # Initialize emotion components
    emotion_analyzer = EmotionAnalyzer()
    emotion_state = EmotionStateMachine()

    logger.info("Cerise API server started")

    yield

    # Cleanup
    logger.info("Shutting down Cerise API server...")
    await message_bus.stop()
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


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="ok", version="0.1.0")


@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreate):
    """Create a new conversation session"""
    global dialogue_engine, personality

    if not dialogue_engine:
        raise HTTPException(status_code=500, detail="Dialogue engine not initialized")

    # Use custom personality or default
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
async def get_session(session_id: str):
    """Get session info"""
    global dialogue_engine

    if not dialogue_engine:
        raise HTTPException(status_code=500, detail="Dialogue engine not initialized")

    session = dialogue_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        message_count=len(session.messages),
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    global dialogue_engine

    if not dialogue_engine:
        raise HTTPException(status_code=500, detail="Dialogue engine not initialized")

    if dialogue_engine.delete_session(session_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message"""
    global dialogue_engine, emotion_analyzer, emotion_state

    if not dialogue_engine:
        raise HTTPException(status_code=500, detail="Dialogue engine not initialized")

    # Get or create session
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
        if emotion_analyzer and emotion_state:
            emotion_result = emotion_analyzer.analyze(response)
            emotion_state.set_emotion(
                emotion_result.primary_emotion.value,
                intensity=emotion_result.confidence,
            )

        current_emotion = emotion_state.current_state.value if emotion_state else "neutral"
        current_intensity = emotion_state.current_intensity if emotion_state else 1.0

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
async def get_emotion():
    """Get current emotion state"""
    global emotion_state

    if not emotion_state:
        return {"emotion": "neutral", "intensity": 1.0}

    return emotion_state.get_animation_params()


@router.post("/emotion")
async def set_emotion(request: EmotionUpdate):
    """Manually set emotion state"""
    global emotion_state

    if not emotion_state:
        raise HTTPException(status_code=500, detail="Emotion state not initialized")

    emotion_state.set_emotion(request.emotion, request.intensity)
    return emotion_state.get_animation_params()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat"""
    global dialogue_engine, emotion_analyzer, emotion_state

    await websocket.accept()
    logger.info("WebSocket connection accepted")

    session: Session | None = None

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "chat")

            if action == "create_session":
                if dialogue_engine:
                    session = dialogue_engine.create_session()
                    await websocket.send_json(
                        {
                            "type": "session_created",
                            "session_id": session.id,
                        }
                    )

            elif action == "chat":
                message = data.get("message", "")
                if not message or not session or not dialogue_engine:
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
                if emotion_analyzer and emotion_state:
                    emotion_result = emotion_analyzer.analyze(full_response)
                    emotion_state.set_emotion(
                        emotion_result.primary_emotion.value,
                        intensity=emotion_result.confidence,
                    )

                await websocket.send_json(
                    {
                        "type": "end",
                        "emotion": emotion_state.current_state.value if emotion_state else "neutral",
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
