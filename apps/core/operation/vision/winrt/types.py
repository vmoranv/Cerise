from __future__ import annotations

from ctypes import POINTER, ArgumentError, FormatError, Structure, c_uint8, c_void_p
from ctypes.wintypes import DWORD, LONG, WORD

HRESULT = LONG  # noqa: F405

VOIDPP = POINTER(c_void_p)

S_OK = 0
S_FALSE = 1

E_FAIL = -2147467259  # 0x80004005L
E_NOTIMPL = -2147467263  # 0x80004001L
E_NOINTERFACE = -2147467262  # 0x80004002L
E_BOUNDS = -2147483637  # 0x8000000BL


def check_hresult(hr):  # noqa: ANN001
    if (hr & 0x80000000) != 0:
        if hr == E_NOTIMPL:
            raise NotImplementedError
        if hr == E_NOINTERFACE:
            raise TypeError("E_NOINTERFACE")
        if hr == E_BOUNDS:
            raise IndexError  # for old style iterator protocol
        e = OSError("[HRESULT 0x%08X] %s" % (hr & 0xFFFFFFFF, FormatError(hr)))  # noqa: UP031
        e.winerror = hr & 0xFFFFFFFF
        raise e
    return hr


class GUID(Structure):
    _fields_ = [("Data1", DWORD), ("Data2", WORD), ("Data3", WORD), ("Data4", c_uint8 * 8)]  # noqa: F405

    def __init__(self, *initwith):  # noqa: ANN001
        if len(initwith) == 1 and isinstance(initwith[0], str):
            strrepr = initwith[0]
            if strrepr.startswith("{"):
                strrepr = strrepr[1:-1]
            part1, part2, part3, part4, part5 = strrepr.split("-", 5)
            self.Data1 = int(part1, 16)
            self.Data2 = int(part2, 16)
            self.Data3 = int(part3, 16)
            self.Data4 = (
                int(part4[0:2], 16),
                int(part4[2:4], 16),
                int(part5[0:2], 16),
                int(part5[2:4], 16),
                int(part5[4:6], 16),
                int(part5[6:8], 16),
                int(part5[8:10], 16),
                int(part5[10:12], 16),
            )
        elif len(initwith) == 4:
            self.Data1, self.Data2, self.Data3, self.Data4 = initwith
        elif len(initwith) == 11:
            self.Data1, self.Data2, self.Data3 = initwith[0], initwith[1], initwith[2]
            self.Data4 = initwith[3:]
        else:
            raise ArgumentError(len(initwith))  # noqa: F405

    def __str__(self) -> str:
        return "%08x-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x" % (  # noqa: UP031
            self.Data1,
            self.Data2,
            self.Data3,
            *list(self.Data4),
        )

    def __repr__(self) -> str:
        return "GUID(%s)" % repr(str(self))  # noqa: UP031

    def __eq__(self, other: object) -> bool:
        return isinstance(other, GUID) and bytes(self) == bytes(other)

    def __hash__(self) -> int:
        # We make GUID instances hashable, although they are mutable.
        return hash(bytes(self))

    def __call__(self, victim):  # noqa: ANN001
        """for use as class decorator"""

        victim.GUID = self
        return victim


REFGUID = POINTER(GUID)
