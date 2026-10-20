"""
Storage Service for CAMS.
Supports:
  - Local filesystem storage (private; served only via signed /api/files URLs)
"""

import hashlib
import hmac
import os
import logging
import time
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Local storage fallback directory
DEFAULT_STORAGE = Path(__file__).resolve().parent.parent.parent / "storage" / "scans"
SCAN_STORAGE_PATH = Path(os.getenv("SCAN_STORAGE_PATH", str(DEFAULT_STORAGE)))
SCAN_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Base URL for local files
STORAGE_BASE_URL = os.getenv("STORAGE_BASE_URL", f"{settings.API_PUBLIC_URL.rstrip('/')}/scans")


def _safe_local_path(relative_path: str) -> Path:
    """Resolve a relative path and ensure it stays inside SCAN_STORAGE_PATH."""
    base = SCAN_STORAGE_PATH.resolve()
    full_path = (base / relative_path).resolve()
    if not full_path.is_relative_to(base):
        raise ValueError(f"Invalid storage path: {relative_path!r}")
    return full_path


def save_bytes(
    data: bytes,
    relative_path: str,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Save bytes to local filesystem.
    Returns the URL string format.
    """
    full_path = _safe_local_path(relative_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)
    url = f"{STORAGE_BASE_URL}/{relative_path}"
    logger.info("Saved to Local: %s (%d bytes)", url, len(data))
    return url


def get_file_bytes(file_url: str) -> bytes:
    """
    Retrieve file bytes from local storage based on the URL.
    """
    relative = file_url.replace(STORAGE_BASE_URL + "/", "")
    full_path = _safe_local_path(relative)
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {full_path}")
    return full_path.read_bytes()


# ─── Private access URLs ────────────────────────────────────────────────────────

def _local_relative(stored_url: str) -> str | None:
    prefix = STORAGE_BASE_URL.rstrip("/") + "/"
    return stored_url[len(prefix):] if stored_url.startswith(prefix) else None


def _local_signature(relative_path: str, expires: int) -> str:
    msg = f"{expires}:{relative_path}".encode()
    key = settings.JWT_SECRET_KEY.encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_local_signature(relative_path: str, expires: int, signature: str) -> bool:
    if expires < int(time.time()):
        return False
    return hmac.compare_digest(_local_signature(relative_path, expires), signature)


def read_local_file(relative_path: str) -> Path | None:
    """Return a safe local file path (or None if missing / outside storage)."""
    try:
        path = _safe_local_path(relative_path)
    except ValueError:
        return None
    return path if path.is_file() else None


def get_access_url(stored_url: str | None, expires_seconds: int = 900) -> str | None:
    """
    Convert a stored (private) file URL into a short-lived access URL.
    Returns an HMAC-signed URL served by /api/files/...
    Unknown URLs are returned unchanged.
    """
    if not stored_url:
        return stored_url

    relative = _local_relative(stored_url)
    if relative is not None:
        exp = int(time.time()) + expires_seconds
        sig = _local_signature(relative, exp)
        return f"{settings.API_PUBLIC_URL.rstrip('/')}/api/files/{exp}/{sig}/{relative}"

    return stored_url
