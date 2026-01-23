"""
ASR 引擎工厂
根据配置创建对应的 ASR 引擎实例
"""

import logging

from ..config import ASRConfig, ASRProvider, InferenceMode
from .base import ASREngine, ASRLanguage
from .cloud_client import CloudASRClient
from .funasr_engine import FunASREngine
from .whisper_engine import WhisperEngine

logger = logging.getLogger(__name__)


class ASREngineFactory:
    """ASR 引擎工厂类"""

    @staticmethod
    def create(config: ASRConfig) -> ASREngine:
        """
        根据配置创建 ASR 引擎

        Args:
            config: ASR 配置

        Returns:
            ASR 引擎实例
        """
        # 语言映射
        lang_map = {
            "auto": ASRLanguage.AUTO,
            "zh": ASRLanguage.CHINESE,
            "en": ASRLanguage.ENGLISH,
            "ja": ASRLanguage.JAPANESE,
        }
        language = lang_map.get(config.language, ASRLanguage.AUTO)

        # 本地推理模式
        if config.mode == InferenceMode.LOCAL:
            if config.provider == ASRProvider.FUNASR:
                logger.info("Creating FunASR engine for local inference")
                return FunASREngine(
                    model_name=config.funasr_model,
                    vad_model=config.funasr_vad_model,
                    punc_model=config.funasr_punc_model,
                    language=language,
                    device=config.funasr_device,
                )
            elif config.provider == ASRProvider.WHISPER:
                logger.info("Creating Whisper engine for local inference")
                return WhisperEngine(
                    model_size=config.whisper_model,
                    language=language,
                    device=config.whisper_device,
                    compute_type=config.whisper_compute_type,
                )
            else:
                raise ValueError(
                    f"Provider {config.provider} not supported for local inference. "
                    f"Use FUNASR or WHISPER."
                )

        # 云端推理模式
        elif config.mode == InferenceMode.CLOUD:
            if config.provider == ASRProvider.CLOUD_API:
                logger.info(f"Creating cloud ASR client: {config.cloud_provider}")
                return CloudASRClient(
                    provider=config.cloud_provider or "custom",
                    api_key=config.cloud_api_key,
                    api_secret=config.cloud_api_secret,
                    api_url=config.cloud_api_url,
                    region=config.cloud_region,
                    language=language,
                    timeout=config.cloud_timeout,
                )
            else:
                # 允许在云端模式下使用本地引擎（混合模式）
                logger.warning(
                    f"Using local provider {config.provider} in cloud mode. "
                    f"Consider using CLOUD_API for better performance."
                )
                return ASREngineFactory._create_local_engine(config, language)

        else:
            raise ValueError(f"Unknown inference mode: {config.mode}")

    @staticmethod
    def _create_local_engine(config: ASRConfig, language: ASRLanguage) -> ASREngine:
        """创建本地引擎的辅助方法"""
        if config.provider == ASRProvider.FUNASR:
            return FunASREngine(
                model_name=config.funasr_model,
                vad_model=config.funasr_vad_model,
                punc_model=config.funasr_punc_model,
                language=language,
                device=config.funasr_device,
            )
        elif config.provider == ASRProvider.WHISPER:
            return WhisperEngine(
                model_size=config.whisper_model,
                language=language,
                device=config.whisper_device,
                compute_type=config.whisper_compute_type,
            )
        else:
            raise ValueError(f"Unknown provider: {config.provider}")


def create_asr_engine(config: ASRConfig) -> ASREngine:
    """Backward-compatible factory wrapper."""
    return ASREngineFactory.create(config)


# 全局引擎实例（单例模式）
_global_engine: ASREngine | None = None


async def get_asr_engine(config: ASRConfig) -> ASREngine:
    """
    获取 ASR 引擎实例（单例）

    Args:
        config: ASR 配置

    Returns:
        已加载的 ASR 引擎实例
    """
    global _global_engine

    if _global_engine is None:
        _global_engine = ASREngineFactory.create(config)
        await _global_engine.load()

    return _global_engine


async def shutdown_asr_engine() -> None:
    """关闭全局 ASR 引擎"""
    global _global_engine

    if _global_engine is not None:
        await _global_engine.unload()
        _global_engine = None
