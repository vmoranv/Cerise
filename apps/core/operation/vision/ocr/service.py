"""
OCR 服务

统一的 OCR 接口，自动选择可用的 OCR 引擎。
"""

from __future__ import annotations

import numpy as np

from ..box import Box
from .base import BaseOCR
from .engines import (
    PaddleOCREngine,
    RapidOCREngine,
    TesseractOCREngine,
    WinRTOCREngine,
)
from .types import OCRResult


class OCRService:
    """OCR 服务

    统一的 OCR 接口，自动选择可用的 OCR 引擎。

    Example:
        ocr = OCRService()
        results = ocr.recognize(frame)
        for r in results:
            _ = (r.text, r.box)

        # 查找特定文字
        box = ocr.find_text(frame, "开始游戏")
        if box:
            _ = box
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
        errors: list[str] = []

        # 优先尝试 RapidOCR（轻量快速）
        try:
            engine = RapidOCREngine()
            engine._get_ocr()
            return engine
        except ImportError:
            errors.append("rapidocr-onnxruntime not installed")

        # 尝试 PaddleOCR
        try:
            engine = PaddleOCREngine(lang=self._lang, use_gpu=self._use_gpu)
            engine._get_ocr()
            return engine
        except ImportError:
            errors.append("paddleocr not installed")

        # 尝试 WinRT OCR（Windows 内置）
        try:
            engine = WinRTOCREngine()
            engine._get_engine()
            return engine
        except ImportError:
            errors.append("winrt ocr not available")

        # 尝试 Tesseract
        try:
            import pytesseract  # noqa: F401

            return TesseractOCREngine(lang="eng+chi_sim")
        except ImportError:
            errors.append("pytesseract not installed")

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
