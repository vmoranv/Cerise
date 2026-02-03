from __future__ import annotations

from ctypes import POINTER, WINFUNCTYPE, byref, c_void_p, cast, windll
from ctypes.wintypes import INT, ULONG

from .idldsl import _new_rtobj, define_winrt_com_method, funcwrap
from .types import GUID, REFGUID, VOIDPP, check_hresult
from .winstring import HSTRING

CoTaskMemFree = windll.ole32.CoTaskMemFree  # noqa: F405
CoTaskMemFree.argtypes = (c_void_p,)  # noqa: F405


@GUID("00000000-0000-0000-C000-000000000046")  # noqa: F405
class IUnknown(c_void_p):  # noqa: F405
    _method_defs = [
        (0, "QueryInterface", WINFUNCTYPE(check_hresult, REFGUID, VOIDPP)(0, "QueryInterface")),  # noqa: F405
        (1, "AddRef", WINFUNCTYPE(ULONG)(1, "AddRef")),  # noqa: F405
        (2, "Release", WINFUNCTYPE(ULONG)(2, "Release")),  # noqa: F405
    ]
    QueryInterface = funcwrap(_method_defs[0][2])
    _AddRef = funcwrap(_method_defs[1][2])
    _Release = funcwrap(_method_defs[2][2])
    _vtblend = 2

    def _detach(self):
        newptr = cast(self, c_void_p)  # noqa: F405
        self.value = None
        return newptr

    def Release(self) -> None:
        if self.value is not None:
            self._Release()
            self.value = None

    def __del__(self) -> None:
        self.Release()

    def astype(self, interface_type):  # noqa: ANN001
        iid = interface_type.GUID
        obj = _new_rtobj(interface_type)
        self.QueryInterface(byref(iid), byref(obj))  # noqa: F405
        return obj

    def __init_subclass__(cls):  # noqa: ANN001
        cls._method_defs = []


class TrustLevel:
    _enum_type_ = INT  # noqa: F405
    BaseTrust = 0
    PartialTrust = 1
    FullTrust = 2


@GUID("AF86E2E0-B12D-4c6a-9C5A-D7AA65101E90")  # noqa: F405
class IInspectable(IUnknown):
    def __class_getitem__(cls, name):  # noqa: ANN001
        return cls

    def __init_subclass__(cls, requires=()):  # noqa: ANN001
        super().__init_subclass__()

    def GetIids(self):  # noqa: N802
        size = ULONG()  # noqa: F405
        ptr = REFGUID()
        self._GetIids(byref(size), byref(ptr))  # noqa: F405
        result = [GUID(str(ptr[i])) for i in range(size.value)]  # noqa: F405
        CoTaskMemFree(ptr)
        return result


define_winrt_com_method(IInspectable, "_GetIids", POINTER(ULONG), POINTER(REFGUID), vtbl=3)  # noqa: F405
define_winrt_com_method(IInspectable, "GetRuntimeClassName", retval=HSTRING, vtbl=4)
define_winrt_com_method(IInspectable, "GetTrustLevel", retval=TrustLevel._enum_type_, vtbl=5)


@GUID("00000035-0000-0000-c000-000000000046")  # noqa: F405
class IActivationFactory(IInspectable):
    pass


define_winrt_com_method(IActivationFactory, "ActivateInstance", retval=IInspectable, vtbl=6)
