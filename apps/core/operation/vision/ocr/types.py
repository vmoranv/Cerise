"""
OCR 类型定义

包含 OCR 结果数据类和引擎协议接口。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import numpy as np

if TYPE_CHECKING:
    from ..box import Box


@dataclass
class OCRResult:
    """OCR 识别结果"""

    text: str
    box: Box
    confidence: float

    def __repr__(self) -> str:
        return f"OCRResult('{self.text}', conf={self.confidence:.2f})"


@runtime_checkable
class OCREngine(Protocol):
    """OCR 引擎协议"""

    def recognize(self, image: np.ndarray) -> list[OCRResult]:
        """识别图像中的文字"""
        ...
