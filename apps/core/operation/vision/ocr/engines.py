"""
OCR 引擎实现

支持的引擎：
- PaddleOCR: 高精度中英文识别
- RapidOCR: 轻量级快速识别
- Tesseract: 开源经典
"""

from __future__ import annotations

import sys

import numpy as np

from ..box import Box
from .base import BaseOCR
from .preprocessor import OCRPreprocessor
from .types import OCRResult


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


class WinRTOCREngine(BaseOCR):
    """WinRT OCR 引擎（Windows.Media.Ocr）

    使用 Windows 内置 OCR（不依赖额外 pip OCR 包）。
    仅在 Windows 上可用。
    """

    def __init__(
        self,
        language_tag: str | None = None,
        preprocessor: OCRPreprocessor | None = None,
    ) -> None:
        super().__init__(preprocessor)
        self.language_tag = language_tag
        self._engine = None
        self._max_image_dimension: int | None = None

    def _get_engine(self):
        if self._engine is not None:
            return self._engine

        if sys.platform != "win32":
            raise ImportError("WinRT OCR is only available on Windows")

        from ..winrt.Windows.Globalization import Language
        from ..winrt.Windows.Media.Ocr import OcrEngine

        if self.language_tag:
            lang = Language.CreateLanguage(self.language_tag)
            if not OcrEngine.IsLanguageSupported(lang):
                raise ImportError(f"WinRT OCR language not supported: {self.language_tag}")
            engine = OcrEngine.TryCreateFromLanguage(lang)
        else:
            engine = OcrEngine.TryCreateFromUserProfileLanguages()

        if getattr(engine, "value", None) is None:
            raise ImportError("WinRT OCR not available (TryCreate returned null)")

        self._engine = engine
        self._max_image_dimension = int(OcrEngine.MaxImageDimension)
        return engine

    def _create_software_bitmap(self, rgba: np.ndarray):
        from ctypes import c_ubyte, c_void_p, cast

        from ..winrt.Windows.Graphics.Imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
        from ..winrt.Windows.Security.Cryptography import CryptographicBuffer

        if rgba.dtype != np.uint8:
            rgba = np.clip(rgba, 0, 255).astype(np.uint8)
        rgba = np.ascontiguousarray(rgba)
        height, width = rgba.shape[:2]
        raw = rgba.tobytes()

        arr = (c_ubyte * len(raw)).from_buffer_copy(raw)
        buffer = CryptographicBuffer.CreateFromByteArray(len(raw), cast(arr, c_void_p))
        return SoftwareBitmap.CreateCopyWithAlphaFromBuffer(
            buffer,
            BitmapPixelFormat.Rgba8,
            width,
            height,
            BitmapAlphaMode.Straight,
        )

    @staticmethod
    def _to_rgba(image: np.ndarray) -> np.ndarray:
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)

        if image.ndim == 2:
            alpha = np.full((*image.shape, 1), 255, dtype=np.uint8)
            rgb = np.stack([image, image, image], axis=-1)
            return np.ascontiguousarray(np.concatenate([rgb, alpha], axis=-1))

        if image.ndim == 3 and image.shape[2] == 3:
            rgb = image[..., ::-1]
            alpha = np.full((image.shape[0], image.shape[1], 1), 255, dtype=np.uint8)
            return np.ascontiguousarray(np.concatenate([rgb, alpha], axis=-1))

        if image.ndim == 3 and image.shape[2] == 4:
            return np.ascontiguousarray(image[..., [2, 1, 0, 3]])

        raise ValueError(f"Unsupported image shape for WinRT OCR: {image.shape}")

    def _recognize_impl(self, image: np.ndarray) -> list[OCRResult]:
        engine = self._get_engine()

        from ..winrt.Windows.Media.Ocr import OcrEngine

        max_dim = self._max_image_dimension or int(OcrEngine.MaxImageDimension)
        orig_h, orig_w = image.shape[:2]
        work = image
        scale_x = 1.0
        scale_y = 1.0

        if max(orig_w, orig_h) > max_dim:
            try:
                import cv2
            except ImportError as exc:
                raise ImportError("opencv-python is required to resize images for WinRT OCR") from exc

            scale = float(max_dim) / float(max(orig_w, orig_h))
            new_w = max(1, int(round(orig_w * scale)))
            new_h = max(1, int(round(orig_h * scale)))
            work = cv2.resize(work, (new_w, new_h), interpolation=cv2.INTER_AREA)
            scale_x = orig_w / float(new_w)
            scale_y = orig_h / float(new_h)

        rgba = self._to_rgba(work)
        software_bitmap = self._create_software_bitmap(rgba)

        try:
            ocr_result = engine.RecognizeAsync(software_bitmap).wait()
        finally:
            try:
                software_bitmap.Close()
            except Exception:
                pass

        results: list[OCRResult] = []

        for line in ocr_result.Lines:
            for word in line.Words:
                rect = word.BoundingRect
                text = str(word.Text)
                if not text:
                    continue

                box = Box(
                    x=rect.x * scale_x,
                    y=rect.y * scale_y,
                    width=rect.width * scale_x,
                    height=rect.height * scale_y,
                    confidence=1.0,
                    name=text,
                )
                results.append(OCRResult(text=text, box=box, confidence=1.0))

        return results
