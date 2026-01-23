"""
OCR 引擎实现

支持的引擎：
- PaddleOCR: 高精度中英文识别
- RapidOCR: 轻量级快速识别
- Tesseract: 开源经典
"""

from __future__ import annotations

import numpy as np

from operation.vision.box import Box
from operation.vision.ocr.base import BaseOCR
from operation.vision.ocr.preprocessor import OCRPreprocessor
from operation.vision.ocr.types import OCRResult


class PaddleOCREngine(BaseOCR):
    """PaddleOCR 引擎

    高精度中英文 OCR，推荐用于游戏文字识别。

    需要安装：pip install paddlepaddle paddleocr
    """

    def __init__(
        self,
        lang: str = "ch",
        use_gpu: bool = False,
        preprocessor: OCRPreprocessor | None = None,
    ) -> None:
        super().__init__(preprocessor)
        self.lang = lang
        self.use_gpu = use_gpu
        self._ocr = None

    def _get_ocr(self):
        """延迟加载 PaddleOCR"""
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR

                self._ocr = PaddleOCR(
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False,
                )
            except ImportError as e:
                raise ImportError("PaddleOCR not installed. Install with: pip install paddlepaddle paddleocr") from e
        return self._ocr

    def _recognize_impl(self, image: np.ndarray) -> list[OCRResult]:
        ocr = self._get_ocr()
        result = ocr.ocr(image, cls=True)

        if not result or not result[0]:
            return []

        results: list[OCRResult] = []
        for line in result[0]:
            box_points = line[0]
            text = line[1][0]
            confidence = line[1][1]

            x_coords = [p[0] for p in box_points]
            y_coords = [p[1] for p in box_points]
            x = int(min(x_coords))
            y = int(min(y_coords))
            w = int(max(x_coords) - x)
            h = int(max(y_coords) - y)

            results.append(
                OCRResult(
                    text=text,
                    box=Box(x=x, y=y, width=w, height=h, confidence=confidence, name=text),
                    confidence=confidence,
                )
            )

        return results


class RapidOCREngine(BaseOCR):
    """RapidOCR 引擎

    轻量级 OCR，速度快，适合实时识别。

    需要安装：pip install rapidocr-onnxruntime
    """

    def __init__(
        self,
        preprocessor: OCRPreprocessor | None = None,
    ) -> None:
        super().__init__(preprocessor)
        self._ocr = None

    def _get_ocr(self):
        """延迟加载 RapidOCR"""
        if self._ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR

                self._ocr = RapidOCR()
            except ImportError as e:
                raise ImportError("RapidOCR not installed. Install with: pip install rapidocr-onnxruntime") from e
        return self._ocr

    def _recognize_impl(self, image: np.ndarray) -> list[OCRResult]:
        ocr = self._get_ocr()
        result, _ = ocr(image)

        if not result:
            return []

        results: list[OCRResult] = []
        for item in result:
            box_points = item[0]
            text = item[1]
            confidence = item[2]

            x_coords = [p[0] for p in box_points]
            y_coords = [p[1] for p in box_points]
            x = int(min(x_coords))
            y = int(min(y_coords))
            w = int(max(x_coords) - x)
            h = int(max(y_coords) - y)

            results.append(
                OCRResult(
                    text=text,
                    box=Box(x=x, y=y, width=w, height=h, confidence=confidence, name=text),
                    confidence=confidence,
                )
            )

        return results


class TesseractOCREngine(BaseOCR):
    """Tesseract OCR 引擎

    开源经典 OCR，需要安装 Tesseract。

    需要安装：pip install pytesseract
    """

    def __init__(
        self,
        lang: str = "eng+chi_sim",
        config: str = "",
        preprocessor: OCRPreprocessor | None = None,
    ) -> None:
        super().__init__(preprocessor)
        self.lang = lang
        self.config = config

    def _recognize_impl(self, image: np.ndarray) -> list[OCRResult]:
        try:
            import pytesseract
        except ImportError as e:
            raise ImportError("pytesseract not installed. Install with: pip install pytesseract") from e

        data = pytesseract.image_to_data(
            image,
            lang=self.lang,
            config=self.config,
            output_type=pytesseract.Output.DICT,
        )

        results: list[OCRResult] = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = data["text"][i].strip()
            if not text:
                continue

            conf = int(data["conf"][i])
            if conf < 0:
                continue

            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]

            results.append(
                OCRResult(
                    text=text,
                    box=Box(x=x, y=y, width=w, height=h, confidence=conf / 100.0, name=text),
                    confidence=conf / 100.0,
                )
            )

        return results
