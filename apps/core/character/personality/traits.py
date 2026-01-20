"""
Personality trait definitions.
"""

from enum import Enum


class PersonalityTrait(Enum):
    """Personality trait dimensions (Big Five + extras)."""

    OPENNESS = "openness"  # 开放性
    CONSCIENTIOUSNESS = "conscientiousness"  # 尽责性
    EXTRAVERSION = "extraversion"  # 外向性
    AGREEABLENESS = "agreeableness"  # 亲和性
    NEUROTICISM = "neuroticism"  # 神经质
    PLAYFULNESS = "playfulness"  # 活泼程度
    CURIOSITY = "curiosity"  # 好奇心
    SHYNESS = "shyness"  # 害羞程度
