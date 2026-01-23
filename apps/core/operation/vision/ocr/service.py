"""
OCR 服务

统一的 OCR 接口，自动选择可用的 OCR 引擎。
"""

from __future__ import annotations

import numpy as np

from operation.vision.box import Box
from operation.vision.ocr.base import BaseOCR
from operation.vision.ocr.engines import (
    PaddleOCREngine,
    RapidOCREngine,
    TesseractOCREngine,
)
from operation.vision.ocr.types import OCRResult


class OCRService:
    """OCR 服务

    统一的 OCR 接口，自动选择可用的 OCR 引擎。

    Example:
        >>> ocr = OCRService()
        >>> results = ocr.recognize(frame)
        >>> for r in results:
        ...     print(f"{r.text} @ {r.box}")
        >>>
        >>> # 查找特定文字
        >>> box = ocr.find_text(frame, "开始游戏")
        >>> if box:
        ...     service.click_box(box)
    """

    def __init__(
        self,
        engine: BaseOCR | None = None,
        lang: str = "ch",
        use_gpu: bool = False,
    ) -> None:
        self._engine = engine
        self._lang = lang
        self._use_gpu = use_gpu

    @property
    def engine(self) -> BaseOCR:
        """获取 OCR 引擎（延迟初始化）"""
        if self._engine is None:
            self._engine = self._auto_select_engine()
        return self._engine

    def _auto_select_engine(self) -> BaseOCR:
        """自动选择可用的 OCR 引擎"""
        # 优先尝试 RapidOCR（轻量快速）
        try:
            return RapidOCREngine()
        except ImportError:
            pass

        # 尝试 PaddleOCR
        try:
            return PaddleOCREngine(lang=self._lang, use_gpu=self._use_gpu)
        except ImportError:
            pass

        # 尝试 Tesseract
        try:
            return TesseractOCREngine(lang="eng+chi_sim")
        except ImportError:
            pass

        raise ImportError(
            "No OCR engine available. Install one of:\n"
            "  - pip install rapidocr-onnxruntime  (recommended)\n"
            "  - pip install paddlepaddle paddleocr\n"
            "  - pip install pytesseract"
        )

    def recognize(self, image: np.ndarray) -> list[OCRResult]:
        """识别图像中的文字"""
        return self.engine.recognize(image)

    def recognize_text(self, image: np.ndarray) -> str:
        """识别并返回纯文本"""
        return self.engine.recognize_text(image)

    def find_text(
        self,
        image: np.ndarray,
        target: str,
        fuzzy: bool = False,
    ) -> Box | None:
        """查找指定文字"""
        return self.engine.find_text(image, target, fuzzy)

    def find_all_text(
        self,
        image: np.ndarray,
        target: str,
        fuzzy: bool = False,
    ) -> list[Box]:
        """查找所有匹配的文字"""
        return self.engine.find_all_text(image, target, fuzzy)
