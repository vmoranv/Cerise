"""Default emotion keyword bundles."""

from .lexicon_keywords_angry import ANGRY_KEYWORDS
from .lexicon_keywords_confused import CONFUSED_KEYWORDS
from .lexicon_keywords_curious import CURIOUS_KEYWORDS
from .lexicon_keywords_disgusted import DISGUSTED_KEYWORDS
from .lexicon_keywords_excited import EXCITED_KEYWORDS
from .lexicon_keywords_fearful import FEARFUL_KEYWORDS
from .lexicon_keywords_happy import HAPPY_KEYWORDS
from .lexicon_keywords_sad import SAD_KEYWORDS
from .lexicon_keywords_shy import SHY_KEYWORDS
from .lexicon_keywords_sleepy import SLEEPY_KEYWORDS
from .lexicon_keywords_surprised import SURPRISED_KEYWORDS
from .types import EmotionType

DEFAULT_KEYWORDS = {
    EmotionType.HAPPY: HAPPY_KEYWORDS,
    EmotionType.SAD: SAD_KEYWORDS,
    EmotionType.ANGRY: ANGRY_KEYWORDS,
    EmotionType.SURPRISED: SURPRISED_KEYWORDS,
    EmotionType.EXCITED: EXCITED_KEYWORDS,
    EmotionType.CURIOUS: CURIOUS_KEYWORDS,
    EmotionType.CONFUSED: CONFUSED_KEYWORDS,
    EmotionType.FEARFUL: FEARFUL_KEYWORDS,
    EmotionType.DISGUSTED: DISGUSTED_KEYWORDS,
    EmotionType.SHY: SHY_KEYWORDS,
    EmotionType.SLEEPY: SLEEPY_KEYWORDS,
}
