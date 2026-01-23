"""TTS adapter factory helpers."""

from __future__ import annotations

from ..config import InferenceMode, TTSConfig, TTSProvider
from .base import TTSAdapter
from .cloud_adapter import CloudTTSAdapter
from .genie_adapter import GenieTTSAdapter

# 全局 TTS 实例
_tts_adapter: TTSAdapter | None = None


class TTSAdapterFactory:
    """TTS 适配器工厂"""

    @staticmethod
    def create(config: TTSConfig) -> TTSAdapter:
        """根据配置创建 TTS 适配器"""
        if config.mode == InferenceMode.CLOUD or config.provider == TTSProvider.CLOUD_API:
            return CloudTTSAdapter(
                provider=config.cloud_provider or "custom",
                api_key=config.cloud_api_key,
                api_url=config.cloud_api_url,
                region=config.cloud_region,
            )
        else:
            characters = config.characters or [config.default_character]
            return GenieTTSAdapter(
                device=config.device,
                model_path=config.local_model_path,
                characters=characters,
            )


async def get_tts_adapter(config: TTSConfig) -> TTSAdapter:
    """获取全局 TTS 适配器（单例）"""
    global _tts_adapter

    if _tts_adapter is None:
        _tts_adapter = TTSAdapterFactory.create(config)
        await _tts_adapter.load()

    return _tts_adapter


async def shutdown_tts_adapter() -> None:
    """关闭全局 TTS 适配器"""
    global _tts_adapter

    if _tts_adapter is not None:
        await _tts_adapter.unload()
        _tts_adapter = None
