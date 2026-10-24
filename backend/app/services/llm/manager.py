"""
CAMS LLM Manager — Central Factory, Database Caching & Resilient Stream Dispatcher.
Loads settings & providers dynamically from DB, caches in Redis (TTL ~30s),
and handles exponential backoff retry and automatic fallback.
"""
import asyncio
import json
import logging
import random
import time
import uuid
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.database import async_session_factory
from app.core.redis import get_redis_client
from app.models.ai_settings import AIProvider, AISettings
from app.services.llm.base import LLMClient, LLMProviderError
from app.services.llm.crypto import decrypt_api_key, encrypt_api_key
from app.services.llm.gemini_client import GeminiClient
from app.services.llm.openai_compat_client import OpenAICompatClient

logger = logging.getLogger(__name__)

CACHE_KEY_ACTIVE_AI_CONFIG = "cams:ai_settings:active"
CACHE_TTL_AI_CONFIG = 30  # 30 seconds TTL


async def invalidate_ai_settings_cache() -> None:
    """Invalidate Redis cache for active AI settings immediately upon update."""
    client = get_redis_client()
    if client is None:
        return
    try:
        await client.delete(CACHE_KEY_ACTIVE_AI_CONFIG)
        logger.info("Invalidated Redis AI settings cache key: %s", CACHE_KEY_ACTIVE_AI_CONFIG)
    except Exception as e:
        logger.warning("Failed to invalidate AI settings cache in Redis: %s", e)


async def seed_default_ai_settings_if_needed(db: AsyncSession) -> tuple[AISettings, AIProvider]:
    """
    Auto-seed default Google Gemini provider and settings if DB tables are empty.
    Allows existing installations to continue operating seamlessly without restart.
    """
    provider_count = await db.scalar(select(func.count(AIProvider.id)))
    if provider_count and provider_count > 0:
        settings_record = await db.scalar(select(AISettings).limit(1))
        if settings_record and settings_record.default_provider_id:
            provider = await db.get(AIProvider, settings_record.default_provider_id)
            if provider:
                return settings_record, provider

    # Seed Gemini provider
    gemini_key = getattr(app_settings, "GEMINI_API_KEY", "").strip()
    encrypted_key = encrypt_api_key(gemini_key) if gemini_key else ""

    default_provider = AIProvider(
        name="Google Gemini",
        type="gemini",
        base_url=None,
        api_key_encrypted=encrypted_key,
        models=["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-pro"],
        enabled=True,
    )
    db.add(default_provider)
    await db.flush()

    default_model = getattr(app_settings, "GEMINI_MODEL", "gemini-3.8-flash")
    ai_settings = AISettings(
        default_provider_id=default_provider.id,
        default_model=default_model,
        fallback_provider_id=None,
        fallback_model=None,
        temperature=0.7,
        max_output_tokens=1500,
        request_timeout_seconds=30,
        max_retries=2,
    )
    db.add(ai_settings)
    await db.commit()
    await db.refresh(default_provider)
    await db.refresh(ai_settings)

    logger.info("Successfully seeded default AIProvider and AISettings from environment.")
    return ai_settings, default_provider


async def get_active_ai_config(db: AsyncSession) -> dict[str, Any]:
    """
    Retrieve active AI configuration. Reads from Redis cache first;
    falls back to Database query and updates cache.
    """
    client = get_redis_client()
    if client:
        try:
            cached_data = await client.get(CACHE_KEY_ACTIVE_AI_CONFIG)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning("Error reading AI settings from Redis: %s", e)

    # Query DB
    settings_record = await db.scalar(select(AISettings).limit(1))
    if not settings_record:
        settings_record, default_prov = await seed_default_ai_settings_if_needed(db)
    else:
        default_prov = await db.get(AIProvider, settings_record.default_provider_id) if settings_record.default_provider_id else None

    fallback_prov = None
    if settings_record and settings_record.fallback_provider_id:
        fallback_prov = await db.get(AIProvider, settings_record.fallback_provider_id)

    # If default_prov is still missing or disabled, find any enabled provider
    if not default_prov or not default_prov.enabled:
        first_enabled = await db.scalar(select(AIProvider).where(AIProvider.enabled.is_(True)).limit(1))
        if first_enabled:
            default_prov = first_enabled

    config_dict = {
        "settings": {
            "default_model": settings_record.default_model if settings_record else "gemini-3.8-flash",
            "fallback_model": settings_record.fallback_model if settings_record else None,
            "temperature": settings_record.temperature if settings_record else 0.7,
            "max_output_tokens": settings_record.max_output_tokens if settings_record else 1500,
            "request_timeout_seconds": settings_record.request_timeout_seconds if settings_record else 30,
            "max_retries": settings_record.max_retries if settings_record else 2,
        },
        "default_provider": {
            "id": str(default_prov.id) if default_prov else None,
            "name": default_prov.name if default_prov else "Mock Provider",
            "type": default_prov.type if default_prov else "mock",
            "base_url": default_prov.base_url if default_prov else None,
            "api_key_encrypted": default_prov.api_key_encrypted if default_prov else "",
            "enabled": default_prov.enabled if default_prov else True,
        } if default_prov else None,
        "fallback_provider": {
            "id": str(fallback_prov.id) if fallback_prov else None,
            "name": fallback_prov.name if fallback_prov else None,
            "type": fallback_prov.type if fallback_prov else None,
            "base_url": fallback_prov.base_url if fallback_prov else None,
            "api_key_encrypted": fallback_prov.api_key_encrypted if fallback_prov else "",
            "models": fallback_prov.models if fallback_prov else [],
            "enabled": fallback_prov.enabled if fallback_prov else False,
        } if fallback_prov and fallback_prov.enabled else None,
    }

    # Store in Redis
    if client:
        try:
            await client.set(
                CACHE_KEY_ACTIVE_AI_CONFIG,
                json.dumps(config_dict),
                ex=CACHE_TTL_AI_CONFIG,
            )
        except Exception as e:
            logger.warning("Error caching AI settings in Redis: %s", e)

    return config_dict


def instantiate_llm_client(provider_dict: Optional[dict[str, Any]], timeout_seconds: float = 30.0) -> LLMClient:
    """Build an instance of LLMClient from provider dict."""
    if not provider_dict:
        from app.services.ai_tutor.provider import MockLLMProvider
        return MockLLMProvider()

    ptype = provider_dict.get("type", "gemini")
    encrypted_key = provider_dict.get("api_key_encrypted", "")
    decrypted_key = decrypt_api_key(encrypted_key) if encrypted_key else ""

    if ptype == "gemini":
        return GeminiClient(api_key=decrypted_key)
    elif ptype == "openai_compatible":
        base_url = provider_dict.get("base_url") or "https://api.openai.com/v1"
        return OpenAICompatClient(
            base_url=base_url,
            api_key=decrypted_key,
            timeout_seconds=timeout_seconds,
        )
    else:
        from app.services.ai_tutor.provider import MockLLMProvider
        return MockLLMProvider()


async def stream_chat_resilient(
    system_instruction: str,
    messages: list[dict[str, str]],
    tool_handler: Optional[Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]] = None,
    db: Optional[AsyncSession] = None,
) -> AsyncGenerator[str, None]:
    """
    Central resilient streaming dispatcher.
    Tries the configured default provider with exponential backoff.
    If exhausted or failing non-recoverably, seamlessly switches to fallback provider.
    """
    # Resolve configuration
    if db is not None:
        config = await get_active_ai_config(db)
    else:
        async with async_session_factory() as session:
            config = await get_active_ai_config(session)

    st_cfg = config.get("settings", {})
    def_prov = config.get("default_provider")
    fb_prov = config.get("fallback_provider")

    temperature = float(st_cfg.get("temperature", 0.7))
    max_tokens = int(st_cfg.get("max_output_tokens", 1500))
    timeout_sec = float(st_cfg.get("request_timeout_seconds", 30))
    max_retries = int(st_cfg.get("max_retries", 2))
    default_model = st_cfg.get("default_model", "gemini-3.8-flash")
    fallback_model = st_cfg.get("fallback_model")

    primary_client = instantiate_llm_client(def_prov, timeout_seconds=timeout_sec)
    primary_name = def_prov.get("name", "Primary") if def_prov else "Mock"

    has_emitted_tokens = False
    last_error: Optional[Exception] = None

    # 1. Primary provider execution with exponential backoff retry
    for attempt in range(1, max_retries + 1):
        try:
            async for chunk in primary_client.stream_chat(
                system_instruction=system_instruction,
                messages=messages,
                model=default_model,
                temperature=temperature,
                max_output_tokens=max_tokens,
                tool_handler=tool_handler,
            ):
                has_emitted_tokens = True
                yield chunk
            return  # Successfully completed primary stream

        except LLMProviderError as e:
            last_error = e
            logger.warning(
                "Primary AI Provider [%s] error (attempt %d/%d): [%s] %s",
                primary_name,
                attempt,
                max_retries,
                e.code,
                e.message,
            )

            # If tokens already sent, client UI has already started receiving body, abort safely
            if has_emitted_tokens:
                raise

            # Retry if eligible
            if e.retryable and attempt < max_retries:
                backoff = 2 ** (attempt - 1)  # 1s, 2s, ...
                jitter = random.uniform(0.1, 0.4)
                delay = backoff + jitter
                logger.info("Retrying primary AI request in %.2fs (attempt %d/%d)...", delay, attempt + 1, max_retries)
                await asyncio.sleep(delay)
                continue
            break

        except Exception as e:
            last_error = e
            logger.error("Unexpected error with primary provider [%s]: %s", primary_name, e)
            if has_emitted_tokens:
                raise
            break

    # 2. Fallback provider execution if primary failed before token emission
    if not has_emitted_tokens and fb_prov and fb_prov.get("enabled"):
        fb_name = fb_prov.get("name", "Fallback")
        fb_models = fb_prov.get("models") or []
        default_fb_model = fb_models[0] if fb_models else "gpt-4o-mini"
        target_fb_model = fallback_model or default_fb_model
        logger.warning(
            "Primary AI Provider [%s] exhausted retries. Engaging fallback provider [%s] with model [%s]...",
            primary_name,
            fb_name,
            target_fb_model,
        )

        fallback_client = instantiate_llm_client(fb_prov, timeout_seconds=timeout_sec)
        try:
            async for chunk in fallback_client.stream_chat(
                system_instruction=system_instruction,
                messages=messages,
                model=target_fb_model,
                temperature=temperature,
                max_output_tokens=max_tokens,
                tool_handler=tool_handler,
            ):
                has_emitted_tokens = True
                yield chunk
            return
        except Exception as fb_err:
            logger.error("Fallback AI Provider [%s] also failed: %s", fb_name, fb_err)
            if has_emitted_tokens:
                raise
            # If fallback also failed, raise structured error with clean message
            fb_err_msg = str(fb_err)
            raise LLMProviderError(
                f"Cả nhà cung cấp AI chính ({primary_name}) và dự phòng ({fb_name}) đều không phản hồi: {fb_err_msg}",
                code="overloaded",
                retryable=True,
                provider_name=fb_name,
            ) from fb_err

    # 3. No fallback or already emitted tokens: re-raise original error
    if last_error:
        if isinstance(last_error, LLMProviderError):
            raise last_error
        raise LLMProviderError(
            "Dịch vụ AI đang gặp sự cố kết nối. Vui lòng thử lại sau.",
            code="other",
            retryable=False,
        ) from last_error
