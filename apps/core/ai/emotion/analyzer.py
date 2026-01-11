"""
Emotion Analyzer

Analyzes text for emotional content and sentiment.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EmotionType(Enum):
    """Primary emotion types"""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    EXCITED = "excited"
    CURIOUS = "curious"
    CONFUSED = "confused"


@dataclass
class EmotionResult:
    """Result of emotion analysis"""

    primary_emotion: EmotionType
    confidence: float  # 0.0 to 1.0
    valence: float  # -1.0 (negative) to 1.0 (positive)
    arousal: float  # 0.0 (calm) to 1.0 (excited)
    dominance: float  # 0.0 (submissive) to 1.0 (dominant)
    secondary_emotions: dict[EmotionType, float] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "primary_emotion": self.primary_emotion.value,
            "confidence": self.confidence,
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance,
            "secondary_emotions": {k.value: v for k, v in self.secondary_emotions.items()},
            "keywords": self.keywords,
        }


class EmotionAnalyzer:
    """Analyzes text for emotional content"""

    # Emotion keyword patterns (simplified)
    EMOTION_PATTERNS: dict[EmotionType, list[str]] = {
        EmotionType.HAPPY: [
            "happy",
            "joy",
            "glad",
            "delighted",
            "pleased",
            "cheerful",
            "开心",
            "高兴",
            "快乐",
            "欢喜",
            "愉快",
            "幸福",
            "嬉しい",
            "楽しい",
            "幸せ",
            "喜び",
            "😊",
            "😀",
            "😁",
            "🥰",
            "❤️",
            "💕",
        ],
        EmotionType.SAD: [
            "sad",
            "unhappy",
            "depressed",
            "gloomy",
            "miserable",
            "难过",
            "伤心",
            "悲伤",
            "沮丧",
            "失落",
            "悲しい",
            "寂しい",
            "辛い",
            "😢",
            "😭",
            "😞",
            "💔",
        ],
        EmotionType.ANGRY: [
            "angry",
            "furious",
            "mad",
            "annoyed",
            "irritated",
            "生气",
            "愤怒",
            "恼火",
            "气愤",
            "怒り",
            "腹立つ",
            "むかつく",
            "😠",
            "😡",
            "🤬",
        ],
        EmotionType.SURPRISED: [
            "surprised",
            "shocked",
            "amazed",
            "astonished",
            "惊讶",
            "震惊",
            "吃惊",
            "意外",
            "驚き",
            "びっくり",
            "😮",
            "😲",
            "🤯",
            "😱",
        ],
        EmotionType.EXCITED: [
            "excited",
            "thrilled",
            "eager",
            "enthusiastic",
            "激动",
            "兴奋",
            "热情",
            "期待",
            "興奮",
            "ワクワク",
            "楽しみ",
            "🎉",
            "🥳",
            "✨",
            "🔥",
        ],
        EmotionType.CURIOUS: [
            "curious",
            "interested",
            "wondering",
            "intrigued",
            "好奇",
            "感兴趣",
            "想知道",
            "気になる",
            "興味",
            "知りたい",
            "🤔",
            "🧐",
        ],
        EmotionType.CONFUSED: [
            "confused",
            "puzzled",
            "perplexed",
            "lost",
            "困惑",
            "迷茫",
            "不明白",
            "搞不懂",
            "わからない",
            "困った",
            "混乱",
            "😕",
            "🤷",
        ],
        EmotionType.FEARFUL: [
            "afraid",
            "scared",
            "frightened",
            "terrified",
            "害怕",
            "恐惧",
            "担心",
            "怖い",
            "恐ろしい",
            "😨",
            "😰",
        ],
    }

    # Valence-Arousal-Dominance values for each emotion
    VAD_VALUES: dict[EmotionType, tuple[float, float, float]] = {
        EmotionType.NEUTRAL: (0.0, 0.3, 0.5),
        EmotionType.HAPPY: (0.8, 0.6, 0.7),
        EmotionType.SAD: (-0.7, 0.3, 0.3),
        EmotionType.ANGRY: (-0.6, 0.8, 0.8),
        EmotionType.SURPRISED: (0.3, 0.8, 0.4),
        EmotionType.FEARFUL: (-0.8, 0.7, 0.2),
        EmotionType.DISGUSTED: (-0.7, 0.5, 0.6),
        EmotionType.EXCITED: (0.7, 0.9, 0.7),
        EmotionType.CURIOUS: (0.4, 0.5, 0.5),
        EmotionType.CONFUSED: (-0.2, 0.5, 0.3),
    }

    def __init__(self):
        # Compile patterns for efficiency
        self._compiled_patterns: dict[EmotionType, re.Pattern] = {}
        for emotion, keywords in self.EMOTION_PATTERNS.items():
            pattern = "|".join(re.escape(kw) for kw in keywords)
            self._compiled_patterns[emotion] = re.compile(pattern, re.IGNORECASE)

    def analyze(self, text: str) -> EmotionResult:
        """Analyze text for emotions"""
        if not text.strip():
            return self._neutral_result()

        # Count emotion matches
        emotion_scores: dict[EmotionType, float] = {}
        matched_keywords: list[str] = []

        for emotion, pattern in self._compiled_patterns.items():
            matches = pattern.findall(text)
            if matches:
                emotion_scores[emotion] = len(matches)
                matched_keywords.extend(matches)

        # Normalize scores
        total_matches = sum(emotion_scores.values()) or 1
        for emotion in emotion_scores:
            emotion_scores[emotion] /= total_matches

        # Determine primary emotion
        if emotion_scores:
            primary_emotion = max(emotion_scores, key=lambda e: emotion_scores[e])
            confidence = emotion_scores[primary_emotion]
        else:
            primary_emotion = EmotionType.NEUTRAL
            confidence = 0.5

        # Get VAD values
        valence, arousal, dominance = self.VAD_VALUES[primary_emotion]

        # Calculate secondary emotions
        secondary = {e: s for e, s in emotion_scores.items() if e != primary_emotion and s > 0.1}

        return EmotionResult(
            primary_emotion=primary_emotion,
            confidence=confidence,
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            secondary_emotions=secondary,
            keywords=list(set(matched_keywords)),
        )

    def _neutral_result(self) -> EmotionResult:
        """Return a neutral emotion result"""
        v, a, d = self.VAD_VALUES[EmotionType.NEUTRAL]
        return EmotionResult(
            primary_emotion=EmotionType.NEUTRAL,
            confidence=1.0,
            valence=v,
            arousal=a,
            dominance=d,
        )

    def analyze_for_character(self, text: str) -> str:
        """Get a simple emotion name for character animation"""
        result = self.analyze(text)
        return result.primary_emotion.value

    def blend_emotions(self, emotions: list[EmotionResult], weights: list[float] | None = None) -> EmotionResult:
        """Blend multiple emotion results"""
        if not emotions:
            return self._neutral_result()

        if weights is None:
            weights = [1.0 / len(emotions)] * len(emotions)

        # Weighted average of VAD
        total_valence = sum(e.valence * w for e, w in zip(emotions, weights))
        total_arousal = sum(e.arousal * w for e, w in zip(emotions, weights))
        total_dominance = sum(e.dominance * w for e, w in zip(emotions, weights))

        # Find closest emotion type
        best_emotion = EmotionType.NEUTRAL
        min_distance = float("inf")

        for emotion, (v, a, d) in self.VAD_VALUES.items():
            distance = (v - total_valence) ** 2 + (a - total_arousal) ** 2 + (d - total_dominance) ** 2
            if distance < min_distance:
                min_distance = distance
                best_emotion = emotion

        return EmotionResult(
            primary_emotion=best_emotion,
            confidence=max(e.confidence for e in emotions),
            valence=total_valence,
            arousal=total_arousal,
            dominance=total_dominance,
        )
