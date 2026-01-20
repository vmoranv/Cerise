"""
Personality Model

Defines character personality traits and generates system prompts.
"""

from dataclasses import dataclass, field

from .personality_emotion import EmotionBiasMixin
from .personality_prompt import PromptMixin
from .personality_serialization import SerializationMixin
from .traits import PersonalityTrait


@dataclass
class PersonalityModel(PromptMixin, EmotionBiasMixin, SerializationMixin):
    """Defines a character's personality."""

    name: str
    traits: dict[PersonalityTrait, float] = field(default_factory=dict)
    background: str = ""
    speaking_style: str = ""
    interests: list[str] = field(default_factory=list)
    quirks: list[str] = field(default_factory=list)
    language: str = "zh"
    voice_character: str = ""
    custom_prompts: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for trait in PersonalityTrait:
            if trait not in self.traits:
                self.traits[trait] = 0.5

    def get_trait(self, trait: PersonalityTrait) -> float:
        """Get a trait value."""
        return self.traits.get(trait, 0.5)

    def set_trait(self, trait: PersonalityTrait, value: float) -> None:
        """Set a trait value (0.0 to 1.0)."""
        self.traits[trait] = max(0.0, min(1.0, value))
