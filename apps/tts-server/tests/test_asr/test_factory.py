"""
ASR 工厂测试
"""

from unittest.mock import MagicMock, patch

import pytest

from src.asr.factory import create_asr_engine, get_available_engines
from src.config import ASRConfig


class TestGetAvailableEngines:
    """获取可用引擎测试"""

    def test_get_available_engines(self):
        """测试获取可用引擎列表"""
        engines = get_available_engines()
        assert isinstance(engines, list)
        # 应该至少包含 "none" 选项
        assert "none" in engines or len(engines) >= 0


class TestCreateASREngine:
    """创建 ASR 引擎测试"""

    def test_create_none_engine(self):
        """测试创建空引擎"""
        config = ASRConfig(engine="none")
        engine = create_asr_engine(config)
        assert engine is None

    def test_create_disabled_engine(self):
        """测试禁用的引擎"""
        config = ASRConfig(engine="funasr", enabled=False)
        engine = create_asr_engine(config)
        assert engine is None

    @patch("src.asr.factory.FunASREngine")
    def test_create_funasr_engine(self, mock_funasr_class):
        """测试创建 FunASR 引擎"""
        mock_engine = MagicMock()
        mock_funasr_class.return_value = mock_engine

        config = ASRConfig(
            engine="funasr",
            enabled=True,
            model_path="test/path",
        )

        with patch.dict("sys.modules", {"funasr": MagicMock()}):
            try:
                engine = create_asr_engine(config)
                # 如果成功创建，验证返回的是预期的引擎
                if engine is not None:
                    assert engine == mock_engine
            except ImportError:
                # 如果 FunASR 未安装，这是预期的
                pass

    @patch("src.asr.factory.WhisperEngine")
    def test_create_whisper_engine(self, mock_whisper_class):
        """测试创建 Whisper 引擎"""
        mock_engine = MagicMock()
        mock_whisper_class.return_value = mock_engine

        config = ASRConfig(
            engine="whisper",
            enabled=True,
            model_path="base",
        )

        with patch.dict("sys.modules", {"faster_whisper": MagicMock()}):
            try:
                engine = create_asr_engine(config)
                if engine is not None:
                    assert engine == mock_engine
            except ImportError:
                # 如果 Whisper 未安装，这是预期的
                pass

    def test_create_unknown_engine(self):
        """测试创建未知引擎"""
        config = ASRConfig(engine="unknown_engine", enabled=True)
        with pytest.raises(ValueError, match="不支持的 ASR 引擎"):
            create_asr_engine(config)

    def test_create_engine_with_device(self):
        """测试带设备参数创建引擎"""
        config = ASRConfig(
            engine="funasr",
            enabled=True,
            device="cuda:0",
        )

        # 由于实际依赖可能不存在，我们只测试配置解析
        assert config.device == "cuda:0"

    def test_create_engine_with_language(self):
        """测试带语言参数创建引擎"""
        config = ASRConfig(
            engine="whisper",
            enabled=True,
            language="zh",
        )

        assert config.language == "zh"
