"""Live2D routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...services.ports import Live2DDriver
from ..dependencies import get_live2d
from ..models import Live2DEmotionUpdate, Live2DParametersUpdate

router = APIRouter()


@router.post("/l2d/emotion")
async def set_live2d_emotion(
    request: Live2DEmotionUpdate,
    live2d: Live2DDriver = Depends(get_live2d),
) -> dict:
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
    live2d: Live2DDriver = Depends(get_live2d),
) -> dict:
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
