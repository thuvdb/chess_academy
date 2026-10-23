"""
CAMS LLM Service Module.
Provides dynamic LLM provider abstraction, OpenAI-compatible integration,
secure Fernet key management, and resilient fallback mechanisms.
"""
from app.services.llm.base import LLMClient, LLMProviderError
from app.services.llm.crypto import (
    AISecurityError,
    decrypt_api_key,
    encrypt_api_key,
    mask_api_key,
    sanitize_sensitive_text,
)
from app.services.llm.gemini_client import GeminiClient
from app.services.llm.manager import (
    get_active_ai_config,
    instantiate_llm_client,
    invalidate_ai_settings_cache,
    seed_default_ai_settings_if_needed,
    stream_chat_resilient,
)
from app.services.llm.openai_compat_client import OpenAICompatClient

__all__ = [
    "LLMClient",
    "LLMProviderError",
    "GeminiClient",
    "OpenAICompatClient",
    "encrypt_api_key",
    "decrypt_api_key",
    "mask_api_key",
    "sanitize_sensitive_text",
    "AISecurityError",
    "get_active_ai_config",
    "invalidate_ai_settings_cache",
    "seed_default_ai_settings_if_needed",
    "stream_chat_resilient",
    "instantiate_llm_client",
]
