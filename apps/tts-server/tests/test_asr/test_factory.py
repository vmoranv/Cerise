"""ASR 工厂测试"""

from unittest.mock import MagicMock, patch

import pytest

from src.asr.factory import ASREngineFactory
from src.config import ASRConfig, ASRProvider, InferenceMode


class TestASREngineFactory:
    """创建 ASR 引擎测试"""

    @patch("src.asr.factory.FunASREngine")
    def test_create_funasr_engine(self, mock_funasr_class):
        """测试创建 FunASR 引擎"""
        mock_engine = MagicMock()
        mock_funasr_class.return_value = mock_engine

        config = ASRConfig(provider=ASRProvider.FUNASR, mode=InferenceMode.LOCAL)
        engine = ASREngineFactory.create(config)
        assert engine == mock_engine

    @patch("src.asr.factory.WhisperEngine")
    def test_create_whisper_engine(self, mock_whisper_class):
        """测试创建 Whisper 引擎"""
        mock_engine = MagicMock()
        mock_whisper_class.return_value = mock_engine

        config = ASRConfig(provider=ASRProvider.WHISPER, mode=InferenceMode.LOCAL)
        engine = ASREngineFactory.create(config)
        assert engine == mock_engine

    def test_create_cloud_engine(self):
        """测试创建 Cloud ASR 客户端"""
        config = ASRConfig(provider=ASRProvider.CLOUD_API, mode=InferenceMode.CLOUD)
        engine = ASREngineFactory.create(config)
        assert engine.__class__.__name__ == "CloudASRClient"

    def test_create_unknown_engine(self):
        """测试创建未知引擎"""
        config = ASRConfig(provider=ASRProvider.CLOUD_API, mode=InferenceMode.LOCAL)
        with pytest.raises(ValueError, match="not supported for local inference"):
            ASREngineFactory.create(config)
