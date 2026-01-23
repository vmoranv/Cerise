"""ASR 基类测试"""

import pytest

from src.asr.base import ASREngine, ASRLanguage, ASRResult, AudioChunk


class DummyASREngine(ASREngine):
    """用于测试的具体 ASR 引擎实现"""

    async def load(self) -> None:
        self._is_loaded = True

    async def unload(self) -> None:
        self._is_loaded = False

    async def transcribe(
        self,
        audio: bytes,
        sample_rate: int = 16000,
        language: ASRLanguage | None = None,
    ) -> ASRResult:
        lang = language or self.language
        return ASRResult(text="测试转录结果", language=lang.value, confidence=0.95)

    async def transcribe_stream(self, audio_stream, language: ASRLanguage | None = None):
        yield ASRResult(text="流式结果1", language="zh", is_final=False)
        yield ASRResult(text="流式结果2", language="zh", is_final=True)


class TestASRResult:
    """ASR 结果测试"""

    def test_create_result(self):
        """测试创建结果"""
        result = ASRResult(text="你好世界", language="zh", confidence=0.95)
        assert result.text == "你好世界"
        assert result.language == "zh"
        assert result.confidence == 0.95
        assert result.is_final is True

    def test_result_defaults(self):
        """测试默认值"""
        result = ASRResult(text="hello")
        assert result.text == "hello"
        assert result.confidence == 1.0
        assert result.is_final is True


class TestAudioChunk:
    """AudioChunk 测试"""

    def test_to_numpy(self):
        """测试转换为 numpy 数组"""
        chunk = AudioChunk(data=b"\x00\x01\x02\x03", sample_rate=16000)
        array = chunk.to_numpy()
        assert array.shape[0] == 2

    def test_to_float32(self):
        """测试转换为 float32 数组"""
        chunk = AudioChunk(data=b"\x00\x00\x00\x00", sample_rate=16000)
        array = chunk.to_float32()
        assert array.shape[0] == 2


class TestASREngine:
    """ASR 引擎抽象类测试"""

    @pytest.fixture
    def engine(self) -> DummyASREngine:
        return DummyASREngine(language=ASRLanguage.CHINESE)

    @pytest.mark.asyncio
    async def test_load_unload(self, engine: DummyASREngine):
        assert not engine.is_loaded
        await engine.load()
        assert engine.is_loaded
        await engine.unload()
        assert not engine.is_loaded

    @pytest.mark.asyncio
    async def test_transcribe(self, engine: DummyASREngine):
        await engine.load()
        result = await engine.transcribe(b"audio_data")
        assert result.text == "测试转录结果"
        assert result.language == "zh"

    @pytest.mark.asyncio
    async def test_transcribe_stream(self, engine: DummyASREngine):
        await engine.load()
        results = []
        async for result in engine.transcribe_stream(iter([b"chunk1", b"chunk2"])):
            results.append(result)
        assert len(results) == 2
        assert results[0].is_final is False
        assert results[1].is_final is True

    @pytest.mark.asyncio
    async def test_context_manager(self, engine: DummyASREngine):
        async with engine:
            assert engine.is_loaded
        assert not engine.is_loaded
