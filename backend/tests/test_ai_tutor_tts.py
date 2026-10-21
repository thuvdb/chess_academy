"""
Unit tests for AI Tutor TTS Provider, Audio Caching, and Rate Limiting.
"""
import uuid
import pytest
from app.services.ai_tutor.tts_provider import (
    MockTTSProvider,
    TTSProviderError,
    get_tts_provider,
)
from app.services.ai_tutor.tts_cache import (
    get_audio_cache_key,
    get_cached_audio_path,
    save_cached_audio,
)
from app.core.redis import check_ai_tutor_tts_rate_limit


@pytest.mark.asyncio
async def test_mock_tts_provider_success():
    """Verify MockTTSProvider produces non-empty audio bytes."""
    provider = MockTTSProvider()
    audio = await provider.generate_speech("Xin chào học viên CAMS", "vi-VN-HoaiMyNeural")
    assert isinstance(audio, bytes)
    assert len(audio) > 100


@pytest.mark.asyncio
async def test_mock_tts_provider_empty_text_error():
    """Verify empty text raises TTSProviderError."""
    provider = MockTTSProvider()
    with pytest.raises(TTSProviderError):
        await provider.generate_speech("   ", "vi-VN-HoaiMyNeural")


def test_audio_cache_key_deterministic():
    """Verify audio cache key is deterministic for identical text and voice."""
    key1 = get_audio_cache_key("Khai cuộc Ý", "vi-VN-HoaiMyNeural")
    key2 = get_audio_cache_key("Khai cuộc Ý", "vi-VN-HoaiMyNeural")
    key3 = get_audio_cache_key("Khai cuộc Ý", "vi-VN-NamMinhNeural")
    assert key1 == key2
    assert key1 != key3


def test_audio_cache_save_and_retrieve(tmp_path, monkeypatch):
    """Verify saving and retrieving cached audio file from disk."""
    import app.services.ai_tutor.tts_cache as tts_cache_module

    # Point cache dir to temp path
    monkeypatch.setattr(tts_cache_module, "_get_cache_dir", lambda: tmp_path)

    text = "Vua e1 đi e2"
    voice = "vi-VN-HoaiMyNeural"
    dummy_bytes = b"ID3\x03\x00\x00\x00\x00\x00\x00dummy_audio_bytes"

    # Initially cache should be missing
    assert get_cached_audio_path(text, voice) is None

    # Save audio to cache
    saved_path = save_cached_audio(text, voice, dummy_bytes)
    assert saved_path.is_file()

    # Now cache hit should return the path
    cached = get_cached_audio_path(text, voice)
    assert cached is not None
    assert cached.read_bytes() == dummy_bytes


@pytest.mark.asyncio
async def test_tts_rate_limit_graceful():
    """Verify check_ai_tutor_tts_rate_limit executes without unhandled exceptions."""
    user_id = uuid.uuid4()
    is_allowed, msg = await check_ai_tutor_tts_rate_limit(user_id)
    # When redis is active or fallback, is_allowed should be a boolean
    assert isinstance(is_allowed, bool)
