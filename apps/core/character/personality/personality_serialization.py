"""
Personality serialization helpers.
"""

from typing import Any, TypeVar

from .traits import PersonalityTrait

SerializationMixinT = TypeVar("SerializationMixinT", bound="SerializationMixin")


class SerializationMixin:
    name: str
    traits: dict[PersonalityTrait, float]
    background: str
    speaking_style: str
    interests: list[str]
    quirks: list[str]
    language: str
    voice_character: str
    custom_prompts: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "traits": {t.value: v for t, v in self.traits.items()},
            "background": self.background,
            "speaking_style": self.speaking_style,
            "interests": self.interests,
            "quirks": self.quirks,
            "language": self.language,
            "voice_character": self.voice_character,
            "custom_prompts": self.custom_prompts,
        }

    @classmethod
    def from_dict(cls: type[SerializationMixinT], data: dict[str, Any]) -> SerializationMixinT:
        """Deserialize from dictionary."""
        traits: dict[PersonalityTrait, float] = {}
        raw_traits = data.get("traits", {})
        if not isinstance(raw_traits, dict):
            raw_traits = {}
        for trait_name, value in raw_traits.items():
            if not isinstance(trait_name, str) or not isinstance(value, (int, float)):
                continue
            try:
                trait = PersonalityTrait(trait_name)
                traits[trait] = float(value)
            except ValueError:
                pass

        return cls(
            name=data.get("name", "未命名"),
            traits=traits,
            background=data.get("background", ""),
            speaking_style=data.get("speaking_style", ""),
            interests=data.get("interests", []),
            quirks=data.get("quirks", []),
            language=data.get("language", "zh"),
            voice_character=data.get("voice_character", ""),
            custom_prompts=data.get("custom_prompts", {}),
        )

    @classmethod
    def create_default(cls: type[SerializationMixinT], name: str = "Cerise") -> SerializationMixinT:
        """Create a default personality."""
        return cls(
            name=name,
            traits={
                PersonalityTrait.OPENNESS: 0.8,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.6,
                PersonalityTrait.EXTRAVERSION: 0.7,
                PersonalityTrait.AGREEABLENESS: 0.8,
                PersonalityTrait.NEUROTICISM: 0.3,
                PersonalityTrait.PLAYFULNESS: 0.7,
                PersonalityTrait.CURIOSITY: 0.8,
                PersonalityTrait.SHYNESS: 0.4,
            },
            background="一个活泼可爱的虚拟主播，喜欢和观众互动聊天",
            speaking_style="使用亲切友好的语气，偶尔会用一些可爱的语气词",
            interests=["游戏", "动漫", "音乐", "聊天"],
            quirks=["喜欢在句尾加语气词", "被夸奖会害羞"],
            language="zh",
        )
