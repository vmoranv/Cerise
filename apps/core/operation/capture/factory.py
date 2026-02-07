"""Capture factory helpers.

The operation layer prefers explicit injection, but a small factory makes it
easy to swap capture methods from config or experiments without touching call
sites.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, cast, overload

import numpy as np

from .base import CaptureMethod
from .fallback import FallbackCapture
from .image import ImageCapture
from .win32_bitblt import Win32BitBltCapture
from .win32_printwindow import Win32PrintWindowCapture

CaptureBackend = Literal["auto", "bitblt", "printwindow", "image"]


def available_capture_backends() -> list[str]:
    return ["auto", "bitblt", "printwindow", "image"]


@overload
def create_capture(
    backend: Literal["image"],
    *,
    loop: bool = True,
    images: Iterable[np.ndarray] | None = None,
) -> CaptureMethod:
    pass


@overload
def create_capture(backend: CaptureBackend = "auto", **kwargs: object) -> CaptureMethod:
    pass


def create_capture(backend: CaptureBackend = "auto", **kwargs: object) -> CaptureMethod:
    backend = cast(CaptureBackend, backend.lower().strip())

    if backend == "bitblt":
        return Win32BitBltCapture()

    if backend == "printwindow":
        return Win32PrintWindowCapture()

    if backend == "image":
        images_obj = kwargs.pop("images", None)
        loop = bool(kwargs.pop("loop", True))
        if kwargs:
            raise TypeError(f"Unknown ImageCapture kwargs: {sorted(kwargs.keys())}")
        images: Iterable[np.ndarray] | None
        if images_obj is None:
            images = None
        elif isinstance(images_obj, Iterable):
            images = cast(Iterable[np.ndarray], images_obj)
        else:
            raise TypeError("images must be an iterable of ndarray")
        return ImageCapture(images=images, loop=loop)

    if backend == "auto":
        if kwargs:
            raise TypeError(f"Unknown create_capture kwargs: {sorted(kwargs.keys())}")
        return FallbackCapture([Win32BitBltCapture(), Win32PrintWindowCapture()])

    raise ValueError(f"Unknown capture backend: {backend!r}. Available: {available_capture_backends()}")
