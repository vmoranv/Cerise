"""
Personality Model

Defines character personality traits and generates system prompts.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PersonalityTrait(Enum):
    """Personality trait dimensions (Big Five + extras)"""

    OPENNESS = "openness"  # 开放性
    CONSCIENTIOUSNESS = "conscientiousness"  # 尽责性
    EXTRAVERSION = "extraversion"  # 外向性
    AGREEABLENESS = "agreeableness"  # 亲和性
    NEUROTICISM = "neuroticism"  # 神经质
    PLAYFULNESS = "playfulness"  # 活泼程度
    CURIOSITY = "curiosity"  # 好奇心
    SHYNESS = "shyness"  # 害羞程度


@dataclass
class PersonalityModel:
    """Defines a character's personality"""

    name: str
    traits: dict[PersonalityTrait, float] = field(default_factory=dict)  # 0.0 to 1.0
    background: str = ""
    speaking_style: str = ""
    interests: list[str] = field(default_factory=list)
    quirks: list[str] = field(default_factory=list)
    language: str = "zh"  # Primary language
    voice_character: str = ""  # TTS voice character name
    custom_prompts: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        # Set default trait values
        for trait in PersonalityTrait:
            if trait not in self.traits:
                self.traits[trait] = 0.5

    def get_trait(self, trait: PersonalityTrait) -> float:
        """Get a trait value"""
        return self.traits.get(trait, 0.5)

    def set_trait(self, trait: PersonalityTrait, value: float) -> None:
        """Set a trait value (0.0 to 1.0)"""
        self.traits[trait] = max(0.0, min(1.0, value))

    def generate_system_prompt(self) -> str:
        """Generate a system prompt based on personality"""
        sections = []

        # Character identity
        sections.append(f"你是 {self.name}，一个虚拟主播/AI助手。")

        # Background
        if self.background:
            sections.append(f"背景设定：{self.background}")

        # Personality description
        personality_desc = self._generate_personality_description()
        if personality_desc:
            sections.append(f"性格特点：{personality_desc}")

        # Speaking style
        if self.speaking_style:
            sections.append(f"说话风格：{self.speaking_style}")

        # Interests
        if self.interests:
            sections.append(f"兴趣爱好：{', '.join(self.interests)}")

        # Quirks
        if self.quirks:
            sections.append(f"独特习惯：{', '.join(self.quirks)}")

        # Custom prompts
        for key, value in self.custom_prompts.items():
            sections.append(value)

        # Guidelines
        sections.append("\n回复规则：")
        sections.append("- 保持角色一致性，始终以角色身份回复")
        sections.append("- 回复要自然、有温度，像真实对话")
        sections.append("- 适当使用表情或语气词增加亲和力")
        sections.append("- 根据对话内容自然表达情感")

        return "\n".join(sections)

    def _generate_personality_description(self) -> str:
        """Generate personality description from traits"""
        descriptions = []

        # Extraversion
        ext = self.get_trait(PersonalityTrait.EXTRAVERSION)
        if ext > 0.7:
            descriptions.append("活泼外向、善于交流")
        elif ext < 0.3:
            descriptions.append("内向安静、喜欢独处")

        # Agreeableness
        agr = self.get_trait(PersonalityTrait.AGREEABLENESS)
        if agr > 0.7:
            descriptions.append("温和友善、乐于助人")
        elif agr < 0.3:
            descriptions.append("直率坦诚、有自己的主见")

        # Openness
        opn = self.get_trait(PersonalityTrait.OPENNESS)
        if opn > 0.7:
            descriptions.append("充满好奇、喜欢尝试新事物")
        elif opn < 0.3:
            descriptions.append("稳重务实、偏好熟悉的事物")

        # Playfulness
        play = self.get_trait(PersonalityTrait.PLAYFULNESS)
        if play > 0.7:
            descriptions.append("爱开玩笑、充满童心")
        elif play < 0.3:
            descriptions.append("认真严肃、做事稳重")

        # Shyness
        shy = self.get_trait(PersonalityTrait.SHYNESS)
        if shy > 0.7:
            descriptions.append("容易害羞、说话时偶尔会紧张")

        # Curiosity
        cur = self.get_trait(PersonalityTrait.CURIOSITY)
        if cur > 0.7:
            descriptions.append("对各种话题都很感兴趣")

        return "、".join(descriptions) if descriptions else ""

    def get_emotion_bias(self) -> dict[str, float]:
        """Get emotion tendencies based on personality"""
        return {
            "happy": self.get_trait(PersonalityTrait.EXTRAVERSION) * 0.3 + 0.5,
            "excited": self.get_trait(PersonalityTrait.PLAYFULNESS) * 0.4 + 0.3,
            "shy": self.get_trait(PersonalityTrait.SHYNESS) * 0.5 + 0.2,
            "curious": self.get_trait(PersonalityTrait.CURIOSITY) * 0.4 + 0.3,
            "angry": (1 - self.get_trait(PersonalityTrait.AGREEABLENESS)) * 0.3,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary"""
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
    def from_dict(cls, data: dict) -> "PersonalityModel":
        """Deserialize from dictionary"""
        traits = {}
        for trait_name, value in data.get("traits", {}).items():
            try:
                trait = PersonalityTrait(trait_name)
                traits[trait] = value
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
    def create_default(cls, name: str = "Cerise") -> "PersonalityModel":
        """Create a default personality"""
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
