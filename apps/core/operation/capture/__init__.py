"""Screen capture module."""

from .base import CaptureMethod
from .factory import CaptureBackend, available_capture_backends, create_capture
from .fallback import FallbackCapture
from .image import ImageCapture
from .win32_bitblt import Win32BitBltCapture
from .win32_printwindow import Win32PrintWindowCapture

__all__ = [
    "CaptureMethod",
    "CaptureBackend",
    "available_capture_backends",
    "create_capture",
    "FallbackCapture",
    "ImageCapture",
    "Win32BitBltCapture",
    "Win32PrintWindowCapture",
]
