"""
ASR 基类测试
"""

import pytest

from src.asr.base import ASREngine, ASRResult


class TestASRResult:
    """ASR 结果测试"""

    def test_create_result(self):
        """测试创建结果"""
        result = ASRResult(
            text="你好世界",
            language="zh",
            confidence=0.95,
            duration=1.5,
        )
        assert result.text == "你好世界"
        assert result.language == "zh"
        assert result.confidence == 0.95
        assert result.duration == 1.5

    def test_result_without_optional_fields(self):
        """测试不带可选字段的结果"""
        result = ASRResult(text="hello")
        assert result.text == "hello"
        assert result.language is None
        assert result.confidence is None
        assert result.duration is None

    def test_result_to_dict(self):
        """测试结果转字典"""
        result = ASRResult(
            text="测试文本",
            language="zh",
            confidence=0.99,
        )
        data = result.model_dump()
        assert data["text"] == "测试文本"
        assert data["language"] == "zh"
        assert data["confidence"] == 0.99


class ConcreteASREngine(ASREngine):
    """用于测试的具体 ASR 引擎实现"""

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> None:
        self._initialized = True

    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> ASRResult:
        return ASRResult(
            text="测试转录结果",
            language=language or "zh",
            confidence=0.95,
        )

    async def transcribe_stream(self, audio_stream, sample_rate: int = 16000):
        yield ASRResult(text="流式结果1", language="zh")
        yield ASRResult(text="流式结果2", language="zh")

    async def cleanup(self) -> None:
        self._initialized = False

    def is_initialized(self) -> bool:
        return self._initialized


class TestASREngine:
    """ASR 引擎抽象类测试"""

    @pytest.fixture
    def engine(self) -> ConcreteASREngine:
        """创建测试引擎"""
        return ConcreteASREngine()

    @pytest.mark.asyncio
    async def test_initialize(self, engine: ConcreteASREngine):
        """测试初始化"""
        assert not engine.is_initialized()
        await engine.initialize()
        assert engine.is_initialized()

    @pytest.mark.asyncio
    async def test_transcribe(self, engine: ConcreteASREngine):
        """测试转录"""
        await engine.initialize()
        result = await engine.transcribe(b"audio_data")
        assert result.text == "测试转录结果"
        assert result.language == "zh"
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_transcribe_with_language(self, engine: ConcreteASREngine):
        """测试带语言参数的转录"""
        await engine.initialize()
        result = await engine.transcribe(b"audio_data", language="en")
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_transcribe_stream(self, engine: ConcreteASREngine):
        """测试流式转录"""
        await engine.initialize()
        results = []
        async for result in engine.transcribe_stream(iter([b"chunk1", b"chunk2"])):
            results.append(result)

        assert len(results) == 2
        assert results[0].text == "流式结果1"
        assert results[1].text == "流式结果2"

    @pytest.mark.asyncio
    async def test_cleanup(self, engine: ConcreteASREngine):
        """测试清理"""
        await engine.initialize()
        assert engine.is_initialized()
        await engine.cleanup()
        assert not engine.is_initialized()

    @pytest.mark.asyncio
    async def test_context_manager(self, engine: ConcreteASREngine):
        """测试上下文管理器"""
        async with engine:
            assert engine.is_initialized()
        assert not engine.is_initialized()
