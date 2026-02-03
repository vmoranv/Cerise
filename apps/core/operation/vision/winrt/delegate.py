from __future__ import annotations

import traceback
from ctypes import HRESULT, POINTER, WINFUNCTYPE, Structure, c_void_p, cast, pointer
from ctypes.wintypes import ULONG

from .inspectable import IUnknown
from .types import E_FAIL, E_NOINTERFACE, GUID, REFGUID, S_OK, VOIDPP

_refmap: dict[int, list] = {}

_typeof_QueryInterface = WINFUNCTYPE(HRESULT, c_void_p, REFGUID, VOIDPP)
_typeof_AddRef = WINFUNCTYPE(ULONG, c_void_p)
_typeof_Release = WINFUNCTYPE(ULONG, c_void_p)


class _impl_delegate_vtbl(Structure):
    _fields_ = [
        ("QueryInterface", _typeof_QueryInterface),
        ("AddRef", _typeof_AddRef),
        ("Release", _typeof_Release),
        ("Invoke", c_void_p),
    ]


class _impl_delegate(Structure):
    _fields_ = [("vtbl", POINTER(_impl_delegate_vtbl))]


def proto(*argtypes, retval=None):  # noqa: ANN001
    if retval is not None:
        argtypes = (*argtypes, POINTER(retval))
    p = WINFUNCTYPE(HRESULT, *argtypes)
    p._retval = retval
    return p


IID_IAgileObject = GUID("94ea2b94-e9cc-49e0-c0ff-ee64ca8f5b90")


class delegatebase:
    @classmethod
    def delegate(cls, func):  # noqa: ANN001
        vtbl = _impl_delegate_vtbl()
        iid = cls.GUID

        def impl_AddRef(this):  # noqa: ANN001,N802
            refcnt = _refmap[this][1] + 1
            _refmap[this][1] = refcnt
            return refcnt

        def impl_QueryInterface(this, refiid, ppunk):  # noqa: ANN001,N802
            try:
                wantiid = refiid.contents
                if wantiid == IUnknown.GUID or wantiid == IID_IAgileObject or wantiid == iid:
                    impl_AddRef(this)
                    ppunk[0] = this
                    return S_OK
                ppunk[0] = None
                return E_NOINTERFACE
            except Exception:
                return E_FAIL

        def impl_Release(this):  # noqa: ANN001,N802
            refcnt = _refmap[this][1] - 1
            _refmap[this][1] = refcnt
            if refcnt == 0:
                del _refmap[this]
            return refcnt

        p = cls._funcproto
        if p._retval is not None:

            def impl_Invoke(this, *args):  # noqa: ANN001,N802
                try:
                    for arg in args:
                        if isinstance(arg, IUnknown) and arg.value is not None:
                            arg._AddRef()
                    retval = func(*args[:-1])
                    args[-1][0] = retval
                    return S_OK
                except Exception:
                    traceback.print_exc()
                    return E_FAIL

        else:

            def impl_Invoke(this, *args, **kwargs):  # noqa: ANN001,N802
                if isinstance(this, IUnknown):
                    this._AddRef()
                try:
                    for arg in args:
                        if isinstance(arg, IUnknown) and arg.value is not None:
                            arg._AddRef()
                    func(*args, **kwargs)
                    return S_OK
                except Exception:
                    traceback.print_exc()
                    return E_FAIL

        cb = p(impl_Invoke)

        vtbl.QueryInterface = _typeof_QueryInterface(impl_QueryInterface)
        vtbl.AddRef = _typeof_AddRef(impl_AddRef)
        vtbl.Release = _typeof_Release(impl_Release)
        vtbl.Invoke = cast(cb, c_void_p)

        obj = _impl_delegate()
        obj.vtbl = pointer(vtbl)
        objptr = pointer(obj)

        objptrval = cast(objptr, c_void_p).value

        keepref = (objptr, obj, vtbl, cb, func)
        _refmap[objptrval] = [keepref, 1]
        return cast(objptr, cls)
