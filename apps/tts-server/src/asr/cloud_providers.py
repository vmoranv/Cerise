"""Cloud ASR provider implementations."""

from __future__ import annotations

import base64
import logging
import time

from .base import ASRLanguage, ASRResult

logger = logging.getLogger(__name__)


class CloudASRProviderMixin:
    async def _transcribe_aliyun(
        self,
        audio: bytes,
        sample_rate: int,
        language: ASRLanguage,
    ) -> ASRResult:
        """阿里云语音识别"""
        # 阿里云 NLS API
        url = self.api_url or "https://nls-gateway.cn-shanghai.aliyuncs.com/stream/v1/asr"

        # 语言映射
        lang_map = {
            ASRLanguage.CHINESE: "zh",
            ASRLanguage.ENGLISH: "en",
            ASRLanguage.JAPANESE: "ja",
            ASRLanguage.AUTO: "zh",
        }

        headers = {
            "Content-Type": "application/octet-stream",
            "X-NLS-Token": self.api_key,
        }

        params = {
            "appkey": self.api_secret,
            "format": "pcm",
            "sample_rate": sample_rate,
            "enable_punctuation_prediction": "true",
            "enable_inverse_text_normalization": "true",
        }

        response = await self._client.post(
            url,
            headers=headers,
            params=params,
            content=audio,
        )
        response.raise_for_status()

        result = response.json()

        if result.get("status") == 20000000:
            return ASRResult(
                text=result.get("result", ""),
                language=lang_map.get(language, "zh"),
                confidence=1.0,
                is_final=True,
            )
        else:
            logger.error(f"Aliyun ASR error: {result}")
            return ASRResult(text="", confidence=0.0)

    async def _transcribe_tencent(
        self,
        audio: bytes,
        sample_rate: int,
        language: ASRLanguage,
    ) -> ASRResult:
        """腾讯云语音识别"""
        url = self.api_url or "https://asr.tencentcloudapi.com"

        # 生成签名
        timestamp = int(time.time())
        audio_base64 = base64.b64encode(audio).decode()

        # 语言映射
        engine_map = {
            ASRLanguage.CHINESE: "16k_zh",
            ASRLanguage.ENGLISH: "16k_en",
            ASRLanguage.JAPANESE: "16k_ja",
            ASRLanguage.AUTO: "16k_zh",
        }

        payload = {
            "ProjectId": 0,
            "SubServiceType": 2,
            "EngineModelType": engine_map.get(language, "16k_zh"),
            "SourceType": 1,
            "VoiceFormat": "pcm",
            "Data": audio_base64,
            "DataLen": len(audio),
        }

        # 构造签名（简化版，实际需要完整的腾讯云签名算法）
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": self.region or "ap-guangzhou",
            "X-TC-Action": "SentenceRecognition",
            "X-TC-Version": "2019-06-14",
        }

        response = await self._client.post(
            url,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

        result = response.json()

        if "Response" in result:
            resp = result["Response"]
            if "Result" in resp:
                return ASRResult(
                    text=resp["Result"],
                    language=language.value if language != ASRLanguage.AUTO else "zh",
                    confidence=1.0,
                    is_final=True,
                )

        logger.error(f"Tencent ASR error: {result}")
        return ASRResult(text="", confidence=0.0)

    async def _transcribe_baidu(
        self,
        audio: bytes,
        sample_rate: int,
        language: ASRLanguage,
    ) -> ASRResult:
        """百度语音识别"""
        # 先获取 access_token
        token_url = "https://aip.baidubce.com/oauth/2.0/token"
        token_response = await self._client.post(
            token_url,
            params={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret,
            },
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            logger.error(f"Baidu token error: {token_data}")
            return ASRResult(text="", confidence=0.0)

        # 语音识别
        url = "https://vop.baidu.com/server_api"

        # 语言映射
        dev_pid_map = {
            ASRLanguage.CHINESE: 1537,  # 普通话
            ASRLanguage.ENGLISH: 1737,  # 英语
            ASRLanguage.AUTO: 1537,
        }

        audio_base64 = base64.b64encode(audio).decode()

        payload = {
            "format": "pcm",
            "rate": sample_rate,
            "channel": 1,
            "cuid": "cerise-tts-server",
            "token": access_token,
            "dev_pid": dev_pid_map.get(language, 1537),
            "speech": audio_base64,
            "len": len(audio),
        }

        response = await self._client.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()

        result = response.json()

        if result.get("err_no") == 0:
            texts = result.get("result", [])
            return ASRResult(
                text=texts[0] if texts else "",
                language=language.value if language != ASRLanguage.AUTO else "zh",
                confidence=1.0,
                is_final=True,
            )

        logger.error(f"Baidu ASR error: {result}")
        return ASRResult(text="", confidence=0.0)

    async def _transcribe_azure(
        self,
        audio: bytes,
        sample_rate: int,
        language: ASRLanguage,
    ) -> ASRResult:
        """Azure 语音识别"""
        region = self.region or "eastus"
        url = f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"

        # 语言映射
        lang_map = {
            ASRLanguage.CHINESE: "zh-CN",
            ASRLanguage.ENGLISH: "en-US",
            ASRLanguage.JAPANESE: "ja-JP",
            ASRLanguage.AUTO: "zh-CN",
        }

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": f"audio/wav; codecs=audio/pcm; samplerate={sample_rate}",
            "Accept": "application/json",
        }

        params = {
            "language": lang_map.get(language, "zh-CN"),
        }

        response = await self._client.post(
            url,
            headers=headers,
            params=params,
            content=audio,
        )
        response.raise_for_status()

        result = response.json()

        if result.get("RecognitionStatus") == "Success":
            return ASRResult(
                text=result.get("DisplayText", ""),
                language=lang_map.get(language, "zh-CN"),
                confidence=result.get("Confidence", 1.0),
                is_final=True,
            )

        logger.error(f"Azure ASR error: {result}")
        return ASRResult(text="", confidence=0.0)

    async def _transcribe_custom(
        self,
        audio: bytes,
        sample_rate: int,
        language: ASRLanguage,
    ) -> ASRResult:
        """自定义 API 调用"""
        if not self.api_url:
            raise ValueError("Custom provider requires api_url")

        # 通用 JSON 格式
        audio_base64 = base64.b64encode(audio).decode()

        payload = {
            "audio": audio_base64,
            "sample_rate": sample_rate,
            "language": language.value if language != ASRLanguage.AUTO else "auto",
            "format": "pcm",
        }

        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = await self._client.post(
            self.api_url,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

        result = response.json()

        # 期望响应格式: {"text": "...", "language": "...", "confidence": 0.95}
        return ASRResult(
            text=result.get("text", ""),
            language=result.get("language", "unknown"),
            confidence=result.get("confidence", 1.0),
            is_final=True,
        )
