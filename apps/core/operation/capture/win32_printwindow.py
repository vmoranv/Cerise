"""Win32 PrintWindow capture backend.

This is a thin wrapper around :class:`~apps.core.operation.capture.win32_bitblt.Win32BitBltCapture`
with ``use_print_window=True``.
"""

from __future__ import annotations

from .win32_bitblt import Win32BitBltCapture


class Win32PrintWindowCapture(Win32BitBltCapture):
    """Window capture using the PrintWindow API."""

    def __init__(self) -> None:
        super().__init__(use_print_window=True)
