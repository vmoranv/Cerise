"""
Personality emotion helpers.
"""

from .traits import PersonalityTrait


class EmotionBiasMixin:
    def get_trait(self, trait: PersonalityTrait) -> float:
        raise NotImplementedError

    def get_emotion_bias(self) -> dict[str, float]:
        """Get emotion tendencies based on personality."""
        return {
            "happy": self.get_trait(PersonalityTrait.EXTRAVERSION) * 0.3 + 0.5,
            "excited": self.get_trait(PersonalityTrait.PLAYFULNESS) * 0.4 + 0.3,
            "shy": self.get_trait(PersonalityTrait.SHYNESS) * 0.5 + 0.2,
            "curious": self.get_trait(PersonalityTrait.CURIOSITY) * 0.4 + 0.3,
            "angry": (1 - self.get_trait(PersonalityTrait.AGREEABLENESS)) * 0.3,
        }
