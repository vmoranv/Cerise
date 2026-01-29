"""Operation service base helpers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from apps.core.contracts.events import (
    OPERATION_ACTION_COMPLETED,
    OPERATION_WINDOW_DISCONNECTED,
    build_operation_action_completed,
    build_operation_window_disconnected,
)
from apps.core.infrastructure import Event, EventBus

from .capture.base import CaptureMethod
from .capture.win32_bitblt import Win32BitBltCapture
from .input.base import Interaction
from .input.win32 import Win32Interaction
from .vision.box import Box

if TYPE_CHECKING:
    import numpy as np

    from .workflow.actions import Action
    from .workflow.types import ActionResult


class OperationServiceBase:
    """Base behavior shared by operation service mixins."""

    def __init__(
        self,
        capture: CaptureMethod | None = None,
        interaction: Interaction | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self._capture = capture or Win32BitBltCapture()
        self._interaction = interaction or Win32Interaction()
        self._bus = bus
        self._hwnd: int = 0
        self._template_cache: dict[str, np.ndarray] = {}
        self._template_dir: Path | None = None

    def _publish_event(self, event_type: str, data: dict[str, object]) -> None:
        if not self._bus:
            return
        self._bus.publish_sync(Event(type=event_type, data=data, source="operation_service"))

    @staticmethod
    def _box_payload(box: Box) -> dict[str, object]:
        return {
            "x": box.x,
            "y": box.y,
            "width": box.width,
            "height": box.height,
            "confidence": box.confidence,
            "name": box.name,
        }

    def _normalize_action_data(self, data: object | None) -> dict[str, object] | None:
        if data is None:
            return None
        if isinstance(data, Box):
            return self._box_payload(data)
        if isinstance(data, dict):
            return data
        return {"value": data}

    def emit_action_result(self, action: Action, result: ActionResult) -> None:
        if not self._bus:
            return
        data_payload = self._normalize_action_data(result.data)
        self._publish_event(
            OPERATION_ACTION_COMPLETED,
            build_operation_action_completed(
                action=action.name,
                action_type=action.__class__.__name__,
                status=result.status.name.lower(),
                message=result.message,
                duration=result.duration,
                data=data_payload,
            ),
        )

    @property
    def hwnd(self) -> int:
        """Current window handle."""
        return self._hwnd

    @property
    def width(self) -> int:
        """Window client width."""
        return self._capture.width

    @property
    def height(self) -> int:
        """Window client height."""
        return self._capture.height

    @property
    def capture(self) -> CaptureMethod:
        """Screen capture instance."""
        return self._capture

    @property
    def interaction(self) -> Interaction:
        """Input interaction instance."""
        return self._interaction

    def set_template_dir(self, path: str | Path) -> None:
        """Set template image directory."""
        self._template_dir = Path(path)

    def clear_template_cache(self) -> None:
        """Clear cached templates."""
        self._template_cache.clear()

    def close(self) -> None:
        """Release resources."""
        if self._hwnd:
            self._publish_event(
                OPERATION_WINDOW_DISCONNECTED,
                build_operation_window_disconnected(self._hwnd),
            )
        self._capture.close()
        self._interaction.close()
        self._hwnd = 0
        self._template_cache.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
