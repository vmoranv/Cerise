"""Lightweight WinRT helpers vendored from ok-script.

This package provides a minimal, dependency-free subset of WinRT bindings
implemented with `ctypes`, sufficient for Windows.Media.Ocr usage.
"""

from __future__ import annotations

from .inspectable import IInspectable, IUnknown
from .types import GUID, HRESULT, REFGUID
from .winstring import HSTRING

__all__ = [
    "GUID",
    "HRESULT",
    "REFGUID",
    "HSTRING",
    "IUnknown",
    "IInspectable",
]
