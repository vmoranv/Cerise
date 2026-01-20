"""WebSocket routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...ai.dialogue import Session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming chat."""
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    services = getattr(websocket.app.state, "services", None)
    if not services:
        await websocket.send_json({"type": "error", "message": "Services not initialized"})
        await websocket.close(code=1011)
        return

    dialogue_engine = services.dialogue_engine
    emotion_service = services.emotion_service
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

                emotion_result = emotion_service.analyze(full_response)
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
