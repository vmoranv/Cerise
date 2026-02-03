from __future__ import annotations

from ctypes import c_int, c_int32

from ....idldsl import GUID, _static_method, define_winrt_com_method, runtimeclass
from ....inspectable import IInspectable
from ...Foundation import IClosable
from ...Storage.Streams import IBuffer


@GUID("689e0708-7eef-483f-963f-da938818e073")
class ISoftwareBitmap(IClosable, IInspectable):
    pass


class BitmapPixelFormat(c_int):
    Rgba8 = 30


class BitmapAlphaMode(c_int):
    Straight = 1


@GUID("DF0385DB-672F-4A9D-806E-C2442F343E86")
class ISoftwareBitmapStatics(IInspectable):
    pass


class SoftwareBitmap(runtimeclass, ISoftwareBitmap):
    CreateCopyWithAlphaFromBuffer = _static_method(ISoftwareBitmapStatics, "CreateCopyWithAlphaFromBuffer")


define_winrt_com_method(
    ISoftwareBitmapStatics,
    "CreateCopyWithAlphaFromBuffer",
    IBuffer,
    BitmapPixelFormat,
    c_int32,
    c_int32,
    BitmapAlphaMode,
    retval=SoftwareBitmap,
    vtbl=10,
)
