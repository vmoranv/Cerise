# AI Module

"""
Cerise AI Core - Dialogue, emotion analysis, and providers
"""

# Providers are always available (no cross-package dependencies)
from .providers import ProviderRegistry


# Lazy imports for modules with cross-package dependencies
def __getattr__(name: str):
    if name == "DialogueEngine":
        from .dialogue import DialogueEngine

        return DialogueEngine
    elif name == "Session":
        from .dialogue import Session

        return Session
    elif name == "EmotionAnalyzer":
        from .emotion import EmotionAnalyzer

        return EmotionAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DialogueEngine",
    "Session",
    "EmotionAnalyzer",
    "ProviderRegistry",
]
