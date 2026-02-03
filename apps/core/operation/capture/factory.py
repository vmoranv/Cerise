"""Capture factory helpers.

The operation layer prefers explicit injection, but a small factory makes it
easy to swap capture methods from config or experiments without touching call
sites.
"""

from __future__ import annotations

from typing import Literal, overload

from .base import CaptureMethod
from .fallback import FallbackCapture
from .image import ImageCapture
from .win32_bitblt import Win32BitBltCapture
from .win32_printwindow import Win32PrintWindowCapture

CaptureBackend = Literal["auto", "bitblt", "printwindow", "image"]


def available_capture_backends() -> list[str]:
    return ["auto", "bitblt", "printwindow", "image"]


@overload
def create_capture(backend: Literal["image"], *, loop: bool = True, images=None) -> CaptureMethod:
    pass


@overload
def create_capture(backend: CaptureBackend = "auto", **kwargs: object) -> CaptureMethod:
    pass


def create_capture(backend: CaptureBackend = "auto", **kwargs: object) -> CaptureMethod:
    backend = backend.lower().strip()  # type: ignore[assignment]

    if backend == "bitblt":
        return Win32BitBltCapture()

    if backend == "printwindow":
        return Win32PrintWindowCapture()

    if backend == "image":
        images = kwargs.pop("images", None)
        loop = bool(kwargs.pop("loop", True))
        if kwargs:
            raise TypeError(f"Unknown ImageCapture kwargs: {sorted(kwargs.keys())}")
        return ImageCapture(images=images, loop=loop)

    if backend == "auto":
        if kwargs:
            raise TypeError(f"Unknown create_capture kwargs: {sorted(kwargs.keys())}")
        return FallbackCapture([Win32BitBltCapture(), Win32PrintWindowCapture()])

    raise ValueError(f"Unknown capture backend: {backend!r}. Available: {available_capture_backends()}")
