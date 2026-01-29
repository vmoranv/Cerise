"""屏幕捕获模块"""

from .base import CaptureMethod
from .win32_bitblt import Win32BitBltCapture

__all__ = ["CaptureMethod", "Win32BitBltCapture"]
