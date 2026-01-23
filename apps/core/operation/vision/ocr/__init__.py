"""
OCR 文字识别模块

支持多种 OCR 后端：
- PaddleOCR (推荐，中英文识别效果好)
- RapidOCR (轻量级，速度快)
- Tesseract (开源经典)
"""

from operation.vision.ocr.base import BaseOCR
from operation.vision.ocr.engines import (
    PaddleOCREngine,
    RapidOCREngine,
    TesseractOCREngine,
)
from operation.vision.ocr.preprocessor import OCRPreprocessor
from operation.vision.ocr.service import OCRService
from operation.vision.ocr.types import OCREngine, OCRResult

__all__ = [
    # Types
    "OCRResult",
    "OCREngine",
    # Preprocessor
    "OCRPreprocessor",
    # Base
    "BaseOCR",
    # Engines
    "PaddleOCREngine",
    "RapidOCREngine",
    "TesseractOCREngine",
    # Service
    "OCRService",
]
