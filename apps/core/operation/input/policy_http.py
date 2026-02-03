"""HTTP-based gamepad policy client."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

import httpx

from .gamepad import GamepadState

if TYPE_CHECKING:
    import numpy as np


class HttpGamepadPolicy:
    """Remote policy client.

    Expected response JSON shape:
    - axes: {str: float}
    - buttons: {str: bool}
    """

    def __init__(
        self,
        endpoint: str,
        *,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
        send_frame: bool = True,
    ) -> None:
        self._endpoint = str(endpoint)
        self._timeout = float(timeout)
        self._headers = dict(headers or {})
        self._send_frame = bool(send_frame)
        self._client = httpx.AsyncClient(timeout=self._timeout, headers=self._headers)

    async def predict(self, *, frame: np.ndarray | None = None, meta: dict[str, Any] | None = None) -> GamepadState:
        payload: dict[str, Any] = {"meta": dict(meta or {})}

        if self._send_frame and frame is not None:
            import cv2

            ok, buf = cv2.imencode(".jpg", frame)
            if ok:
                payload["frame_jpeg_b64"] = base64.b64encode(buf.tobytes()).decode("ascii")

        resp = await self._client.post(self._endpoint, json=payload)
        resp.raise_for_status()
        data = resp.json()

        axes = {str(k): float(v) for k, v in dict(data.get("axes", {})).items()}
        buttons = {str(k): bool(v) for k, v in dict(data.get("buttons", {})).items()}
        return GamepadState(axes=axes, buttons=buttons)

    async def close(self) -> None:
        await self._client.aclose()
