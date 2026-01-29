"""
OCR 文字识别模块

支持多种 OCR 后端：
- PaddleOCR (推荐，中英文识别效果好)
- RapidOCR (轻量级，速度快)
- Tesseract (开源经典)
"""

from .base import BaseOCR
from .engines import (
    PaddleOCREngine,
    RapidOCREngine,
    TesseractOCREngine,
)
from .preprocessor import OCRPreprocessor
from .service import OCRService
from .types import OCREngine, OCRResult

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
