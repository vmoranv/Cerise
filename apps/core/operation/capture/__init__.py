"""屏幕捕获模块"""

from operation.capture.base import CaptureMethod
from operation.capture.win32_bitblt import Win32BitBltCapture

__all__ = ["CaptureMethod", "Win32BitBltCapture"]
