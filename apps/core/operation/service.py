"""Operation layer main service."""

from __future__ import annotations

from .service_base import OperationServiceBase
from .service_capture import OperationCaptureMixin
from .service_input import OperationInputMixin
from .service_vision import OperationVisionMixin
from .service_window import OperationWindowMixin


class OperationService(
    OperationServiceBase,
    OperationWindowMixin,
    OperationCaptureMixin,
    OperationVisionMixin,
    OperationInputMixin,
):
    """Unified automation service for capture, vision, and input."""
