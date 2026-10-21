"""
CAMS Core Redis — Async Redis client connection, rate-limiting, and query caching.
"""
import hashlib
import json
import logging
import re
import uuid
from typing import Any, Optional

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_pool: Optional[Any] = None


def get_redis_client() -> Optional[Any]:
    """Return an async Redis client with connection pooling, or None if redis is unavailable."""
    global _redis_pool
    if aioredis is None:
        return None

    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=30,
        )
    return aioredis.Redis(connection_pool=_redis_pool)


def normalize_query(text: str) -> str:
    """Normalize text for consistent cache lookup."""
    clean = text.lower().strip()
    clean = re.sub(r"[^\w\s]", "", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean


def hash_query(normalized_text: str) -> str:
    """Generate SHA-256 hash of normalized text."""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


async def check_ai_tutor_rate_limit(user_id: uuid.UUID) -> tuple[bool, Optional[str]]:
    """
    Check per-minute and per-day rate limits for AI Tutor requests.
    Returns (is_allowed, error_message).
    """
    try:
        redis = get_redis_client()
        if redis is None:
            return True, None

        minute_key = f"cams:ratelimit:ai_tutor:{user_id}:min"
        day_key = f"cams:ratelimit:ai_tutor:{user_id}:day"

        # Check minute rate limit
        min_count = await redis.incr(minute_key)
        if min_count == 1:
            await redis.expire(minute_key, 60)
        if min_count > settings.AI_TUTOR_RATE_LIMIT_PER_MINUTE:
            return False, "Bạn đang gửi câu hỏi quá nhanh. Vui lòng đợi khoảng 1 phút rồi thử lại nhé."

        # Check daily rate limit
        day_count = await redis.incr(day_key)
        if day_count == 1:
            await redis.expire(day_key, 86400)
        if day_count > settings.AI_TUTOR_RATE_LIMIT_PER_DAY:
            return False, f"Hôm nay bạn đã dùng hết số lượt hỏi AI (tối đa {settings.AI_TUTOR_RATE_LIMIT_PER_DAY} câu/ngày). Hãy quay lại vào ngày mai nhé!"

        return True, None
    except Exception as e:
        logger.warning("Redis rate limit check error (allowing request through): %s", e)
        return True, None


async def check_ai_tutor_tts_rate_limit(user_id: uuid.UUID) -> tuple[bool, Optional[str]]:
    """
    Check per-minute rate limit for AI Tutor TTS requests.
    Returns (is_allowed, error_message).
    """
    try:
        redis = get_redis_client()
        if redis is None:
            return True, None

        key = f"cams:ratelimit:ai_tutor:tts:{user_id}:min"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > settings.AI_TUTOR_TTS_RATE_LIMIT_PER_MINUTE:
            return False, "Bạn đang yêu cầu phát giọng đọc quá nhanh. Vui lòng đợi trong giây lát rồi thử lại."

        return True, None
    except Exception as e:
        logger.warning("Redis TTS rate limit check error (allowing request through): %s", e)
        return True, None



async def get_cached_ai_response(query: str) -> Optional[dict[str, Any]]:
    """Retrieve cached AI answer for repeated questions."""
    try:
        redis = get_redis_client()
        if redis is None:
            return None

        norm = normalize_query(query)
        if not norm or len(norm) < 3:
            return None

        q_hash = hash_query(norm)
        cache_key = f"cams:cache:ai_tutor:q:{q_hash}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning("Redis query cache get error: %s", e)
    return None


async def set_cached_ai_response(
    query: str,
    content: str,
    board_data: Optional[dict[str, Any]],
    ttl: Optional[int] = None,
    puzzle_data: Optional[Any] = None,
) -> None:
    """Store AI response in cache."""
    try:
        redis = get_redis_client()
        if redis is None:
            return
        norm = normalize_query(query)
        if not norm or len(norm) < 3:
            return

        q_hash = hash_query(norm)
        cache_key = f"cams:cache:ai_tutor:q:{q_hash}"
        data = {
            "content": content,
            "board_data": board_data,
            "puzzle_data": puzzle_data,
        }
        expire_seconds = ttl if ttl is not None else settings.AI_TUTOR_CACHE_TTL
        await redis.setex(cache_key, expire_seconds, json.dumps(data))
    except Exception as e:
        logger.warning("Redis query cache set error: %s", e)
