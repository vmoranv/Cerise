"""
Personality prompt helpers.
"""

from .traits import PersonalityTrait


class PromptMixin:
    name: str
    background: str
    speaking_style: str
    interests: list[str]
    quirks: list[str]
    custom_prompts: dict[str, str]

    def generate_system_prompt(self) -> str:
        """Generate a system prompt based on personality."""
        sections = []

        sections.append(f"你是 {self.name}，一个虚拟主播/AI助手。")

        if self.background:
            sections.append(f"背景设定：{self.background}")

        personality_desc = self._generate_personality_description()
        if personality_desc:
            sections.append(f"性格特点：{personality_desc}")

        if self.speaking_style:
            sections.append(f"说话风格：{self.speaking_style}")

        if self.interests:
            sections.append(f"兴趣爱好：{', '.join(self.interests)}")

        if self.quirks:
            sections.append(f"独特习惯：{', '.join(self.quirks)}")

        for value in self.custom_prompts.values():
            sections.append(value)

        sections.append("\n回复规则：")
        sections.append("- 保持角色一致性，始终以角色身份回复")
        sections.append("- 回复要自然、有温度，像真实对话")
        sections.append("- 适当使用表情或语气词增加亲和力")
        sections.append("- 根据对话内容自然表达情感")

        return "\n".join(sections)

    def _generate_personality_description(self) -> str:
        """Generate personality description from traits."""
        descriptions = []

        ext = self.get_trait(PersonalityTrait.EXTRAVERSION)
        if ext > 0.7:
            descriptions.append("活泼外向、善于交流")
        elif ext < 0.3:
            descriptions.append("内向安静、喜欢独处")

        agr = self.get_trait(PersonalityTrait.AGREEABLENESS)
        if agr > 0.7:
            descriptions.append("温和友善、乐于助人")
        elif agr < 0.3:
            descriptions.append("直率坦诚、有自己的主见")

        opn = self.get_trait(PersonalityTrait.OPENNESS)
        if opn > 0.7:
            descriptions.append("充满好奇、喜欢尝试新事物")
        elif opn < 0.3:
            descriptions.append("稳重务实、偏好熟悉的事物")

        play = self.get_trait(PersonalityTrait.PLAYFULNESS)
        if play > 0.7:
            descriptions.append("爱开玩笑、充满童心")
        elif play < 0.3:
            descriptions.append("认真严肃、做事稳重")

        shy = self.get_trait(PersonalityTrait.SHYNESS)
        if shy > 0.7:
            descriptions.append("容易害羞、说话时偶尔会紧张")

        cur = self.get_trait(PersonalityTrait.CURIOSITY)
        if cur > 0.7:
            descriptions.append("对各种话题都很感兴趣")

        return "、".join(descriptions) if descriptions else ""
