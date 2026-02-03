"""Capture protocol interface.

This module defines the shared protocol only.

Concrete implementations live in:
- `apps/core/operation/capture/win32_bitblt.py`
- `apps/core/operation/capture/win32_printwindow.py`
- `apps/core/operation/capture/image.py`
- `apps/core/operation/capture/fallback.py`

See `apps/core/operation/capture/factory.py` for unified backend selection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import numpy as np


@runtime_checkable
class CaptureMethod(Protocol):
    """屏幕捕获方法协议

    所有捕获后端实现必须符合此协议接口。
    支持的后端包括：
    - Win32 BitBlt (兼容性最好)
    - Windows Graphics Capture (WGC, 性能更好)
    - D3D11 Desktop Duplication (DirectX 应用)
    """

    @property
    def width(self) -> int:
        """捕获区域宽度"""
        pass

    @property
    def height(self) -> int:
        """捕获区域高度"""
        pass

    @property
    def hwnd(self) -> int:
        """当前绑定的窗口句柄"""
        pass

    def connect(self, hwnd: int) -> bool:
        """连接到目标窗口

        Args:
            hwnd: 目标窗口句柄

        Returns:
            连接是否成功
        """
        pass

    def connected(self) -> bool:
        """检查是否已连接到窗口"""
        pass

    def get_frame(self) -> np.ndarray | None:
        """获取当前帧

        Returns:
            BGR 格式的图像数组，失败返回 None
        """
        pass

    def close(self) -> None:
        """释放资源"""
        pass
