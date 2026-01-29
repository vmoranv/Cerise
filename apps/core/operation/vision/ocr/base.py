"""
OCR 基类
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ..box import Box
from .preprocessor import OCRPreprocessor
from .types import OCRResult


class BaseOCR(ABC):
    """OCR 基类"""

    def __init__(self, preprocessor: OCRPreprocessor | None = None) -> None:
        self.preprocessor = preprocessor or OCRPreprocessor()

    @abstractmethod
    def _recognize_impl(self, image: np.ndarray) -> list[OCRResult]:
        """实际识别实现"""
        ...

    def recognize(self, image: np.ndarray) -> list[OCRResult]:
        """识别图像中的文字"""
        processed = self.preprocessor.process(image)
        return self._recognize_impl(processed)

    def recognize_text(self, image: np.ndarray) -> str:
        """识别并返回纯文本"""
        results = self.recognize(image)
        return " ".join(r.text for r in results)

    def find_text(
        self,
        image: np.ndarray,
        target: str,
        fuzzy: bool = False,
    ) -> Box | None:
        """查找指定文字

        Args:
            image: 输入图像
            target: 目标文字
            fuzzy: 是否模糊匹配

        Returns:
            包含目标文字的区域
        """
        results = self.recognize(image)

        for r in results:
            if fuzzy:
                if target.lower() in r.text.lower():
                    return r.box
            else:
                if target == r.text:
                    return r.box

        return None

    def find_all_text(
        self,
        image: np.ndarray,
        target: str,
        fuzzy: bool = False,
    ) -> list[Box]:
        """查找所有匹配的文字"""
        results = self.recognize(image)
        boxes: list[Box] = []

        for r in results:
            if fuzzy:
                if target.lower() in r.text.lower():
                    boxes.append(r.box)
            else:
                if target == r.text:
                    boxes.append(r.box)

        return boxes
