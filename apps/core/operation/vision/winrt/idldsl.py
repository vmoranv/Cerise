from __future__ import annotations

import enum
from _ctypes import _SimpleCData
from ctypes import (
    POINTER,
    WINFUNCTYPE,
    byref,
    c_bool,
    c_double,
    c_float,
    c_int32,
    c_int64,
    c_uint8,
    c_uint32,
    c_uint64,
)
from functools import lru_cache

from . import roapi
from .types import GUID, check_hresult


class CtypesEnum(enum.IntEnum):
    """A ctypes-compatible IntEnum superclass."""

    @classmethod
    def from_param(cls, obj):  # noqa: ANN001
        return int(obj)


def STDMETHOD(index, name, *argtypes):  # noqa: ANN001
    proto = WINFUNCTYPE(check_hresult, *argtypes)  # noqa: F405
    func = proto(index, name)
    return func


def define_winrt_com_method(  # noqa: ANN001
    interface,
    name,
    *argtypes,
    retval=None,
    propget=None,
    propput=None,
    vtbl: int = next,
):
    if vtbl is next:
        vtbl = interface._vtblend + 1
    if getattr(interface, "_method_defs", None) is None:
        setattr(interface, "_method_defs", [])
    if interface._method_defs is getattr(interface.__mro__[1], "_method_defs", None):
        setattr(interface, "_method_defs", [])

    if retval is not None:
        comfunc = STDMETHOD(vtbl, name, *argtypes, POINTER(retval))
        if retval.__mro__[1] is _SimpleCData:

            def func(this, *args, **kwargs):  # noqa: ANN001
                obj = this.astype(interface)
                result = retval()
                comfunc(obj, *args, byref(result), **kwargs)  # noqa: F405
                return result.value

        else:

            def func(this, *args, **kwargs):  # noqa: ANN001
                obj = this.astype(interface)
                result = _new_rtobj(retval)
                comfunc(obj, *args, byref(result), **kwargs)  # noqa: F405
                return result

        interface._method_defs.append((vtbl, name, comfunc))
        setattr(interface, "_" + name, comfunc)
        setattr(interface, name, func)

    elif propget is not None:
        comgetter = STDMETHOD(vtbl, name, *argtypes, POINTER(propget))
        setattr(interface, name, comgetter)
        interface._method_defs.append((vtbl, name, comgetter))
        if name.startswith("get_"):
            propname = name[4:]
            if propname in interface.__dict__:
                setter = interface.__dict__[propname].fset
            else:
                setter = None

            if propget.__mro__[1] is _SimpleCData:

                def getter(this, *args, **kwargs):  # noqa: ANN001
                    obj = this.astype(interface)
                    result = propget()
                    comgetter(obj, *args, byref(result), **kwargs)  # noqa: F405
                    return result.value

            else:

                def getter(this, *args, **kwargs):  # noqa: ANN001
                    obj = this.astype(interface)
                    result = _new_rtobj(propget)
                    comgetter(obj, *args, byref(result), **kwargs)  # noqa: F405
                    return result

            setattr(interface, propname, property(getter, setter))

    elif propput is not None:
        comsetter = STDMETHOD(vtbl, name, *argtypes, propput)
        interface._method_defs.append((vtbl, name, comsetter))
        setattr(interface, name, comsetter)
        if name.startswith("put_"):
            propname = name[4:]
            if propname in interface.__dict__:
                getter = interface.__dict__[propname].fget
            else:
                getter = None

            def setter(this, *args, **kwargs):  # noqa: ANN001
                obj = this.astype(interface)
                comsetter(obj, *args, **kwargs)

            setattr(interface, propname, property(getter, setter))

    else:
        comfunc = STDMETHOD(vtbl, name, *argtypes)

        def func(this, *args, **kwargs):  # noqa: ANN001
            obj = this.astype(interface)
            comfunc(obj, *args, **kwargs)

        interface._method_defs.append((vtbl, name, comfunc))
        setattr(interface, name, funcwrap(func))

    if vtbl > interface._vtblend:
        interface._vtblend = vtbl


class classproperty(property):
    def __get__(self, obj, type_):  # noqa: ANN001
        return self.fget.__get__(None, type_)()

    def __set__(self, obj, value):  # noqa: ANN001
        cls = type(obj)
        return self.fset.__get__(None, cls)(value)


def _static_propget(interface, propname):  # noqa: ANN001
    def getter(cls):  # noqa: ANN001
        statics = roapi.GetActivationFactory(cls._runtimeclass_name, interface)
        return getattr(statics, propname)

    return classproperty(classmethod(getter))


def _static_method(interface, methodname):  # noqa: ANN001
    def func(cls, *args, **kwargs):  # noqa: ANN001
        statics = roapi.GetActivationFactory(cls._runtimeclass_name, interface)
        return getattr(statics, methodname)(*args, **kwargs)

    return classmethod(func)


def funcwrap(f):  # noqa: ANN001
    return lambda *args, **kw: f(*args, **kw)


def _non_activatable_init(self):  # noqa: ANN001
    raise NotImplementedError("non-activatable runtime class " + self._runtimeclass_name)


_predefined_sigs = {
    c_uint8: "u1",
    c_int32: "i4",
    c_uint32: "u4",
    c_int64: "i8",
    c_uint64: "u8",
    c_float: "f4",
    c_double: "f8",
    c_bool: "b1",
    str: "string",
    "char16": "c2",
    GUID: "g16",
}


def _runtimeclass_signature(classname, default_iid):  # noqa: ANN001
    return "rc(%s;{%s})" % (classname, str(default_iid).lower())  # noqa: UP031


def _get_type_signature(clazz):  # noqa: ANN001
    if hasattr(clazz, "_signature"):
        return clazz._signature
    if isruntimeclass(clazz):
        return _runtimeclass_signature(clazz._runtimeclass_name, clazz.__mro__[2].GUID)
    if hasattr(clazz, "GUID"):
        return "{%s}" % str(clazz.GUID).lower()  # noqa: UP031
    if clazz in _predefined_sigs:
        return _predefined_sigs[clazz]
    raise TypeError("no signature for type", clazz)


_runtimeclass_registry: dict[str, type] = {}


class runtimeclass:
    def __init_subclass__(cls):  # noqa: ANN001
        mod1 = cls.__module__.split(".")
        mod2 = __name__.split(".")
        i = 0
        for i in range(min(len(mod1), len(mod2))):
            if mod1[i] != mod2[i]:
                break
        name = mod1[i:]
        name.append(cls.__name__)
        clsname = ".".join(name)
        cls._runtimeclass_name = clsname
        _runtimeclass_registry[clsname] = cls


def isruntimeclass(clazz) -> bool:  # noqa: ANN001
    return clazz.__mro__[1] is runtimeclass


def _new_rtobj(clazz):  # noqa: ANN001
    if isruntimeclass(clazz):
        return clazz.__mro__[2].__new__(clazz)
    return clazz()


def generics_cache(func):  # noqa: ANN001
    def wrapped(*types):  # noqa: ANN001
        if types in wrapped.known_types:
            return wrapped.known_types[types]
        return func(*types)

    wrapped.known_types = {}
    return wrapped


def _sigoctets_to_uuid(octets: bytes) -> str:
    import hashlib

    digest = hashlib.sha1()
    digest.update(octets)
    uuidbytes = bytearray(digest.digest()[:16])
    octet6 = uuidbytes[6]
    octet6 = (octet6 & 0b00001111) | 0b01010000
    uuidbytes[6] = octet6
    octet8 = uuidbytes[8]
    octet8 = (octet8 & 0b00111111) | 0b10000000
    uuidbytes[8] = octet8
    return "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x" % tuple(uuidbytes)  # noqa: UP031


@lru_cache
def generate_parameterized_attrs(piid, *generics):  # noqa: ANN001
    newsig = "pinterface({%s};%s)" % (piid, ";".join(map(_get_type_signature, generics)))  # noqa: UP031
    sigoctets = b"\x11\xf4z\xd5{sB\xc0\xab\xae\x87\x8b\x1e\x16\xad\xee" + newsig.encode("utf-8")
    guid = _sigoctets_to_uuid(sigoctets)
    return {"IID": guid, "_signature": newsig, "_typeparam": generics}


def fqn(t):  # noqa: ANN001
    return t.__qualname__


def pinterface_type(name, piid, typeparams, bases):  # noqa: ANN001
    attrs = generate_parameterized_attrs(piid, *typeparams)
    cls = type("%s(%s)" % (name, ",".join(map(fqn, typeparams))), bases, attrs)  # noqa: UP031
    return cls


def define_winrt_com_delegate(cls, *argtypes, retval=None):  # noqa: ANN001
    from . import delegate

    if retval is not None:
        define_winrt_com_method(cls, "Invoke", *argtypes, POINTER(retval), vtbl=3)
    else:
        define_winrt_com_method(cls, "Invoke", *argtypes, vtbl=3)
    cls._funcproto = delegate.proto(cls, *argtypes, retval=retval)
