from __future__ import annotations

from ctypes import POINTER, byref, windll
from ctypes.wintypes import INT
from functools import lru_cache

from .inspectable import IActivationFactory, IInspectable
from .types import REFGUID, check_hresult
from .winstring import HSTRING

combase = windll.LoadLibrary("combase.dll")  # noqa: F405
RoGetActivationFactory = combase.RoGetActivationFactory
RoGetActivationFactory.argtypes = (HSTRING, REFGUID, POINTER(IInspectable))
RoGetActivationFactory.restype = check_hresult


class RO_INIT_TYPE(INT):  # noqa: F405
    RO_INIT_SINGLETHREADED = 0
    RO_INIT_MULTITHREADED = 1


RoInitialize = combase.RoInitialize
RoInitialize.argtypes = (RO_INIT_TYPE,)
RoInitialize.restype = check_hresult


@lru_cache
def GetActivationFactory(classname, interface=IActivationFactory):  # noqa: ANN001,N802
    insp = interface()
    RoGetActivationFactory(classname, interface.GUID, byref(insp))  # noqa: F405
    return insp


RoInitialize(RO_INIT_TYPE.RO_INIT_SINGLETHREADED)
