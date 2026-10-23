"""
CAMS LLM Crypto Utilities — Fernet API Key Encryption & Masking.
Ensures API keys are encrypted at rest in the database and never leaked in logs or API responses.
"""
import base64
import re
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class AISecurityError(Exception):
    """Raised when encryption or security preconditions are not met."""
    pass


def _get_fernet(secret: Optional[str] = None) -> Fernet:
    """Initialize Fernet cipher using configured AI_SETTINGS_SECRET."""
    if secret is not None:
        key = secret.strip()
    else:
        key = getattr(settings, "AI_SETTINGS_SECRET", "").strip()

    if not key:
        raise AISecurityError(
            "Biến môi trường AI_SETTINGS_SECRET chưa được cấu hình. "
            "Vui lòng thiết lập khóa Fernet 32-byte (base64) trong file .env."
        )

    try:
        # Validate base64 length (Fernet keys are 32 raw bytes, 44 chars in base64)
        raw_bytes = base64.urlsafe_b64decode(key.encode("utf-8"))
        if len(raw_bytes) != 32:
            raise ValueError("Key must be 32 bytes")
        return Fernet(key.encode("utf-8"))
    except Exception as e:
        raise AISecurityError(
            f"AI_SETTINGS_SECRET không hợp lệ ({type(e).__name__}). "
            "Khóa Fernet phải là chuỗi base64 32 bytes hợp lệ (sinh bằng Fernet.generate_key())."
        ) from e


def encrypt_api_key(raw_key: Optional[str], secret: Optional[str] = None) -> str:
    """
    Encrypt a plaintext API key with Fernet.
    Returns the encrypted token as a UTF-8 string.
    """
    if not raw_key or not raw_key.strip():
        return ""
    cipher = _get_fernet(secret)
    encrypted_bytes = cipher.encrypt(raw_key.strip().encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_api_key(encrypted_key: Optional[str], secret: Optional[str] = None) -> str:
    """
    Decrypt a Fernet encrypted API key token.
    Returns the plaintext string.
    """
    if not encrypted_key or not encrypted_key.strip():
        return ""
    cipher = _get_fernet(secret)
    try:
        decrypted_bytes = cipher.decrypt(encrypted_key.strip().encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken as e:
        raise AISecurityError(
            "Không thể giải mã API key (InvalidToken). Khóa AI_SETTINGS_SECRET có thể đã bị thay đổi."
        ) from e


def mask_api_key(raw_key: Optional[str]) -> str:
    """
    Mask an API key for safe display in UI/API responses.
    Example: 'sk-Cw4H12345678903GC' -> 'sk-Cw4H...3GC'
    """
    if not raw_key:
        return ""
    clean = raw_key.strip()
    length = len(clean)
    if length == 0:
        return ""
    if length > 12:
        return f"{clean[:7]}...{clean[-4:]}"
    if length > 6:
        return f"{clean[:3]}...{clean[-2:]}"
    return "****"


def sanitize_sensitive_text(text: str, known_secrets: Optional[list[str]] = None) -> str:
    """
    Scrub sensitive credentials (API keys, Bearer tokens) from error strings or logs.
    """
    if not text:
        return ""

    sanitized = text

    # Redact known keys
    if known_secrets:
        for secret in known_secrets:
            if secret and len(secret) >= 4:
                sanitized = sanitized.replace(secret, "[REDACTED_API_KEY]")

    # Redact Authorization header patterns
    sanitized = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", r"\1[REDACTED_TOKEN]", sanitized, flags=re.IGNORECASE)
    # Redact URL key query params e.g. ?key=AIza...
    sanitized = re.sub(r"(key=)[A-Za-z0-9_\-]{8,}", r"\1[REDACTED_KEY]", sanitized, flags=re.IGNORECASE)
    # Redact typical API key formats: sk-..., AIza...
    sanitized = re.sub(r"sk-[A-Za-z0-9_\-]{16,}", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(r"AIza[0-9A-Za-z\-_]{35}", "[REDACTED_API_KEY]", sanitized)

    return sanitized
