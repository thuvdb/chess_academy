"""
CAMS AI Tutor — TTS Audio File Cache.
Caches generated MP3 files on disk using SHA-256 hash of cleaned text + voice.
"""
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base cache path relative to project root or upload dir
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "tts_cache"


def _get_cache_dir() -> Path:
    """Return cache directory, ensuring it exists."""
    cache_path = Path(settings.AI_TUTOR_TTS_CACHE_DIR)
    if not cache_path.is_absolute():
        base = Path(__file__).resolve().parent.parent.parent.parent
        cache_path = (base / cache_path).resolve()
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


def get_audio_cache_key(text: str, voice: str) -> str:
    """Compute SHA-256 hash key for text and voice combination."""
    payload = f"{voice}:{text.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_cached_audio_path(text: str, voice: str) -> Optional[Path]:
    """
    Check if a valid cached MP3 file exists for the given text and voice.
    Returns Path if valid and not expired, else None.
    """
    try:
        cache_dir = _get_cache_dir()
        key = get_audio_cache_key(text, voice)
        file_path = cache_dir / f"{key}.mp3"

        if file_path.is_file():
            # Check expiration TTL
            file_age = time.time() - file_path.stat().st_mtime
            if file_age <= settings.AI_TUTOR_TTS_CACHE_TTL:
                return file_path
            else:
                # Expired cache
                try:
                    file_path.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception as e:
        logger.warning("Error checking TTS cache: %s", e)
    return None


def save_cached_audio(text: str, voice: str, audio_bytes: bytes) -> Path:
    """Save audio bytes into the disk cache."""
    cache_dir = _get_cache_dir()
    key = get_audio_cache_key(text, voice)
    file_path = cache_dir / f"{key}.mp3"

    try:
        file_path.write_bytes(audio_bytes)
    except Exception as e:
        logger.error("Failed to write TTS cache file %s: %s", file_path, e)
    return file_path
