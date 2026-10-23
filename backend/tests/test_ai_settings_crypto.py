"""
Unit tests for CAMS AI Crypto utilities (Fernet encryption, decryption, masking, and sanitization).
"""
import pytest
from cryptography.fernet import Fernet

from app.services.llm.crypto import (
    AISecurityError,
    decrypt_api_key,
    encrypt_api_key,
    mask_api_key,
    sanitize_sensitive_text,
)


def test_fernet_encryption_and_decryption():
    test_secret = Fernet.generate_key().decode()
    original_key = "sk-Cw4H9988776655443322113GC"

    encrypted = encrypt_api_key(original_key, secret=test_secret)
    assert encrypted != original_key
    assert isinstance(encrypted, str)

    decrypted = decrypt_api_key(encrypted, secret=test_secret)
    assert decrypted == original_key


def test_empty_or_whitespace_key_handling():
    test_secret = Fernet.generate_key().decode()
    assert encrypt_api_key("", secret=test_secret) == ""
    assert encrypt_api_key(None, secret=test_secret) == ""
    assert decrypt_api_key("", secret=test_secret) == ""
    assert decrypt_api_key(None, secret=test_secret) == ""


def test_missing_or_invalid_secret_raises_error():
    with pytest.raises(AISecurityError) as exc_info:
        encrypt_api_key("some_key", secret="")
    assert "chưa được cấu hình" in str(exc_info.value)

    with pytest.raises(AISecurityError) as exc_info:
        encrypt_api_key("some_key", secret="invalid_base64_secret")
    assert "không hợp lệ" in str(exc_info.value)


def test_mask_api_key():
    # Long key: first 7 + "..." + last 4
    assert mask_api_key("sk-Cw4H9988776655443322113GC") == "sk-Cw4H...13GC"
    # Medium key (> 6, <= 12)
    assert mask_api_key("sk-1234567") == "sk-...67"
    # Short key (<= 6)
    assert mask_api_key("12345") == "****"
    # Empty
    assert mask_api_key("") == ""
    assert mask_api_key(None) == ""


def test_sanitize_sensitive_text():
    raw_key = "sk-secret1234567890abcdef"
    error_msg = f"Failed connecting to https://api.openai.com/v1 with Authorization: Bearer {raw_key}"
    sanitized = sanitize_sensitive_text(error_msg, known_secrets=[raw_key])

    assert raw_key not in sanitized
    assert "[REDACTED" in sanitized

    gemini_key = "AIzaSyD-123456789012345678901234567890"
    url_err = f"Error calling https://generativelanguage.googleapis.com/v1beta?key={gemini_key}"
    sanitized_url = sanitize_sensitive_text(url_err)
    assert gemini_key not in sanitized_url
    assert "[REDACTED" in sanitized_url
