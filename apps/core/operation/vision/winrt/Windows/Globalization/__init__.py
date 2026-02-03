from __future__ import annotations

from ....idldsl import GUID, _static_method, define_winrt_com_method, runtimeclass
from ....inspectable import IInspectable
from ....winstring import HSTRING


@GUID("EA79A752-F7C2-4265-B1BD-C4DEC4E4F080")
class ILanguage(IInspectable):
    pass


@GUID("9B0252AC-0C27-44F8-B792-9793FB66C63E")
class ILanguageFactory(IInspectable):
    pass


class Language(runtimeclass, ILanguage):
    CreateLanguage = _static_method(ILanguageFactory, "CreateLanguage")


define_winrt_com_method(ILanguage, "get_LanguageTag", propget=HSTRING, vtbl=6)
define_winrt_com_method(ILanguage, "get_DisplayName", propget=HSTRING, vtbl=7)
define_winrt_com_method(ILanguage, "get_NativeName", propget=HSTRING, vtbl=8)
define_winrt_com_method(ILanguage, "get_Script", propget=HSTRING, vtbl=9)

define_winrt_com_method(ILanguageFactory, "CreateLanguage", HSTRING, retval=Language, vtbl=6)
