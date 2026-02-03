"""
OCR 基类
"""

from __future__ import annotations

from abc import ABC

import numpy as np

from ..box import Box
from .preprocessor import OCRPreprocessor
from .types import OCRResult


class BaseOCR(ABC):
    """OCR 基类"""

    def __init__(self, preprocessor: OCRPreprocessor | None = None) -> None:
        self.preprocessor = preprocessor or OCRPreprocessor()
        self._delegate: BaseOCR | None = None

    def _recognize_impl(self, image: np.ndarray) -> list[OCRResult]:
        """实际识别实现（默认：自动选择可用 OCR 引擎并委托调用）"""
        delegate = self._get_or_create_delegate()
        return delegate._recognize_impl(image)

    def _get_or_create_delegate(self) -> BaseOCR:
        if self._delegate is not None:
            return self._delegate

        from .engines import PaddleOCREngine, RapidOCREngine, TesseractOCREngine, WinRTOCREngine

        errors: list[str] = []

        try:
            engine = RapidOCREngine(preprocessor=self.preprocessor)
            engine._get_ocr()
            self._delegate = engine
            return engine
        except ImportError as exc:
            errors.append(str(exc))

        try:
            engine = PaddleOCREngine(lang="ch", use_gpu=False, preprocessor=self.preprocessor)
            engine._get_ocr()
            self._delegate = engine
            return engine
        except ImportError as exc:
            errors.append(str(exc))

        try:
            engine = WinRTOCREngine(preprocessor=self.preprocessor)
            engine._get_engine()
            self._delegate = engine
            return engine
        except ImportError as exc:
            errors.append(str(exc))

        try:
            import pytesseract  # noqa: F401

            engine = TesseractOCREngine(lang="eng+chi_sim", preprocessor=self.preprocessor)
            self._delegate = engine
            return engine
        except ImportError as exc:
            errors.append(str(exc))

        detail = "\n".join(f"  - {err}" for err in errors if err)
        msg = (
            "No OCR engine available. Install one of:\n"
            "  - pip install rapidocr-onnxruntime  (recommended)\n"
            "  - pip install paddlepaddle paddleocr\n"
            "  - pip install pytesseract\n"
        )
        if detail:
            msg = f"{msg}\nImport errors:\n{detail}\n"
        raise ImportError(msg)

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
