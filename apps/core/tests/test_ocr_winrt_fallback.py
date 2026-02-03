"""Tests for OCR fallback selection."""

from apps.core.operation.vision.ocr.base import BaseOCR
from apps.core.operation.vision.ocr.engines import PaddleOCREngine, RapidOCREngine, WinRTOCREngine
from apps.core.operation.vision.ocr.service import OCRService


def _raise_import_error(*args, **kwargs):  # noqa: ANN002,ANN003
    raise ImportError("missing dependency")


def test_ocr_service_selects_winrt_when_pip_engines_missing(monkeypatch):
    """OCRService should fall back to WinRT OCR before Tesseract."""
    monkeypatch.setattr(RapidOCREngine, "_get_ocr", _raise_import_error)
    monkeypatch.setattr(PaddleOCREngine, "_get_ocr", _raise_import_error)
    monkeypatch.setattr(WinRTOCREngine, "_get_engine", lambda self: object())

    ocr = OCRService()
    assert isinstance(ocr.engine, WinRTOCREngine)


def test_baseocr_delegate_selects_winrt_when_pip_engines_missing(monkeypatch):
    """BaseOCR should fall back to WinRT OCR before Tesseract."""
    monkeypatch.setattr(RapidOCREngine, "_get_ocr", _raise_import_error)
    monkeypatch.setattr(PaddleOCREngine, "_get_ocr", _raise_import_error)
    monkeypatch.setattr(WinRTOCREngine, "_get_engine", lambda self: object())

    base = BaseOCR()
    delegate = base._get_or_create_delegate()
    assert isinstance(delegate, WinRTOCREngine)
