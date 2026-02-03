from __future__ import annotations

from ctypes import c_uint32, c_void_p

from ....idldsl import GUID, _non_activatable_init, _static_method, define_winrt_com_method, runtimeclass
from ....inspectable import IInspectable
from ...Storage.Streams import IBuffer


@GUID("320B7E22-3CB0-4CDF-8663-1D28910065EB")
class ICryptographicBufferStatics(IInspectable):
    pass


class CryptographicBuffer(runtimeclass):
    __init__ = _non_activatable_init
    CreateFromByteArray = _static_method(ICryptographicBufferStatics, "CreateFromByteArray")


define_winrt_com_method(
    ICryptographicBufferStatics,
    "CreateFromByteArray",
    c_uint32,
    c_void_p,
    retval=IBuffer,
    vtbl=9,
)
