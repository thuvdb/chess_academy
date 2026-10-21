"""
CAMS AI Tutor — TTS Provider Abstraction.
Wraps edge-tts library with non-blocking async execution,
and provides a MockTTSProvider for testing and offline environments.
"""
import asyncio
import logging
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)

# Valid silent MP3 frame (1 frame of MPEG1 Layer 3, 128kbps, 44.1kHz stereo)
MOCK_SILENT_MP3 = (
    b"\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


class TTSProviderError(Exception):
    """Exception raised when speech synthesis fails."""
    def __init__(self, message: str = "Không thể tạo giọng đọc lúc này. Vui lòng thử lại sau."):
        self.message = message
        super().__init__(self.message)


class TTSProvider(ABC):
    """Abstract interface for speech synthesis providers."""

    @abstractmethod
    async def generate_speech(self, text: str, voice: str) -> bytes:
        """Synthesize text to MP3 audio bytes."""
        pass


class EdgeTTSProvider(TTSProvider):
    """Microsoft Edge TTS async provider."""

    async def generate_speech(self, text: str, voice: str) -> bytes:
        if not text.strip():
            raise TTSProviderError("Nội dung cần đọc không được để trống.")

        try:
            import edge_tts

            communicate = edge_tts.Communicate(text=text, voice=voice)
            audio_buffer = bytearray()

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.extend(chunk["data"])

            if not audio_buffer:
                raise TTSProviderError("Dịch vụ giọng đọc không trả về dữ liệu âm thanh.")

            return bytes(audio_buffer)

        except asyncio.TimeoutError:
            logger.warning("Edge TTS request timed out.")
            raise TTSProviderError("Quá thời gian chờ khi tạo giọng đọc. Vui lòng thử lại.")
        except Exception as e:
            logger.error("Edge TTS error (%s): %s", type(e).__name__, e)
            raise TTSProviderError("Dịch vụ giọng đọc đang tạm thời gián đoạn. Vui lòng thử lại sau.")


class MockTTSProvider(TTSProvider):
    """Mock TTS provider returning silent dummy MP3 data for tests and offline environments."""

    async def generate_speech(self, text: str, voice: str) -> bytes:
        await asyncio.sleep(0.01)
        if not text.strip():
            raise TTSProviderError("Nội dung cần đọc không được để trống.")
        return MOCK_SILENT_MP3 * 5


def get_tts_provider() -> TTSProvider:
    """Factory function returning the configured TTS provider."""
    provider_name = settings.AI_TUTOR_TTS_PROVIDER.lower().strip()
    if provider_name == "mock":
        return MockTTSProvider()
    return EdgeTTSProvider()
