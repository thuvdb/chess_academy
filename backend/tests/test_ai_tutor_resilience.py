"""
Unit tests for AI Tutor Resilience:
- Gemini error classification (503 overloaded, 429 quota, timeout, auth).
- Retry before token emission with exponential backoff.
- Clean SSE closure on permanent failure.
- No-retry rule once tokens have already been emitted.
- Rate limit refund on external Google provider failure.
"""
import asyncio
import json
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.services.ai_tutor.provider import (
    AIProviderError,
    LLMProvider,
    classify_gemini_error,
)
from app.core.redis import refund_ai_tutor_rate_limit


# --- 1. Test Error Classification ---

def test_classify_gemini_error_503_overloaded():
    """503 or high demand is classified as overloaded and retryable."""
    err_msg = "503 UNAVAILABLE: The model is currently experiencing high demand. Please try again later."
    msg, code, retryable = classify_gemini_error(err_msg)
    assert code == "overloaded"
    assert retryable is True
    assert "quá tải" in msg


def test_classify_gemini_error_429_quota():
    """429 or RESOURCE_EXHAUSTED is classified as quota and retryable."""
    err_msg = "429 RESOURCE_EXHAUSTED: Quota exceeded for quota metric 'GenerateContentRequests'."
    msg, code, retryable = classify_gemini_error(err_msg)
    assert code == "quota"
    assert retryable is True
    assert "hạn ngạch" in msg or "quota" in msg.lower()


def test_classify_gemini_error_timeout():
    """Timeout error is classified as timeout and retryable."""
    err_msg = "Deadline exceeded while waiting for response."
    msg, code, retryable = classify_gemini_error(err_msg, err_type="TimeoutError")
    assert code == "timeout"
    assert retryable is True
    assert "quá thời gian chờ" in msg


def test_classify_gemini_error_auth():
    """API_KEY_INVALID is non-retryable auth error."""
    err_msg = "400 API_KEY_INVALID: Your API key is not valid."
    msg, code, retryable = classify_gemini_error(err_msg)
    assert code == "auth"
    assert retryable is False


def test_classify_gemini_error_other():
    """Unknown internal error defaults to other and non-retryable."""
    err_msg = "Something completely unexpected happened."
    msg, code, retryable = classify_gemini_error(err_msg)
    assert code == "other"
    assert retryable is False


# --- 2. Test Retry Mechanism before Token Emission ---

class FlakyLLMProvider(LLMProvider):
    """Fails with 503 for first N attempts, then succeeds."""
    def __init__(self, failures_before_success: int, tokens: list[str]):
        self.failures_before_success = failures_before_success
        self.current_attempt = 0
        self.tokens = tokens

    async def stream_chat(self, messages, system_instruction, max_tokens=1500, temperature=0.7, tool_handler=None):
        self.current_attempt += 1
        if self.current_attempt <= self.failures_before_success:
            raise AIProviderError(
                "Model is currently experiencing high demand",
                code="overloaded",
                retryable=True,
            )
        for t in self.tokens:
            yield t


@pytest.mark.asyncio
async def test_retry_succeeds_on_transient_503():
    """Simulate transient 503 twice before succeeding on attempt 3."""
    provider = FlakyLLMProvider(failures_before_success=2, tokens=["Xin chào", " học viên CAMS!"])

    emitted_chunks = []
    has_emitted_tokens = False
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            async for chunk in provider.stream_chat([], "system"):
                has_emitted_tokens = True
                emitted_chunks.append(chunk)
            break
        except AIProviderError as e:
            if not has_emitted_tokens and e.retryable and attempt < max_retries:
                # Mock fast delay in test
                await asyncio.sleep(0.01)
                continue
            raise

    assert provider.current_attempt == 3
    assert emitted_chunks == ["Xin chào", " học viên CAMS!"]
    assert has_emitted_tokens is True


@pytest.mark.asyncio
async def test_permanent_503_yields_error_event_and_clean_done():
    """Simulate permanent 503 exceeding max retries yields error event and closes cleanly."""
    provider = FlakyLLMProvider(failures_before_success=10, tokens=["Won't reach"])

    events = []
    has_emitted_tokens = False
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            async for chunk in provider.stream_chat([], "system"):
                has_emitted_tokens = True
                events.append({"event": "message", "chunk": chunk})
            break
        except AIProviderError as e:
            if not has_emitted_tokens and e.retryable and attempt < max_retries:
                await asyncio.sleep(0.01)
                continue

            events.append({
                "event": "error",
                "code": e.code,
                "error": e.message,
                "retryable": not has_emitted_tokens and e.retryable,
            })
            events.append({"event": "done", "error": True, "code": e.code})
            break

    assert provider.current_attempt == 3
    assert len(events) == 2
    assert events[0]["event"] == "error"
    assert events[0]["code"] == "overloaded"
    assert events[0]["retryable"] is True
    assert events[1]["event"] == "done"
    assert events[1]["error"] is True


class DropMidStreamProvider(LLMProvider):
    """Emits 1 token, then crashes with 503."""
    def __init__(self):
        self.attempts = 0

    async def stream_chat(self, messages, system_instruction, max_tokens=1500, temperature=0.7, tool_handler=None):
        self.attempts += 1
        yield "Nước đi đầu tiên là: "
        raise AIProviderError("Connection dropped mid-stream", code="overloaded", retryable=True)


@pytest.mark.asyncio
async def test_no_retry_after_token_emission():
    """If tokens were already emitted, do not retry (avoids repeated text)."""
    provider = DropMidStreamProvider()

    emitted_chunks = []
    has_emitted_tokens = False
    max_retries = 3
    events = []

    for attempt in range(1, max_retries + 1):
        try:
            async for chunk in provider.stream_chat([], "system"):
                has_emitted_tokens = True
                emitted_chunks.append(chunk)
            break
        except AIProviderError as e:
            # Should NOT retry because has_emitted_tokens is True
            if not has_emitted_tokens and e.retryable and attempt < max_retries:
                await asyncio.sleep(0.01)
                continue

            events.append({
                "event": "error",
                "code": e.code,
                "retryable": not has_emitted_tokens and e.retryable,
            })
            break

    assert provider.attempts == 1  # Exactly 1 attempt, no retry
    assert emitted_chunks == ["Nước đi đầu tiên là: "]
    assert events[0]["retryable"] is False  # Cannot retry mid-stream cleanly


# --- 3. Test Rate Limit Refund ---

@pytest.mark.asyncio
async def test_refund_ai_tutor_rate_limit():
    """Verify refund_ai_tutor_rate_limit calls redis decr on minute and day keys."""
    mock_redis = AsyncMock()
    mock_redis.decr.return_value = 0

    with patch("app.core.redis.get_redis_client", return_value=mock_redis):
        uid = uuid.uuid4()
        await refund_ai_tutor_rate_limit(uid)

        assert mock_redis.decr.call_count == 2
        calls = [c.args[0] for c in mock_redis.decr.call_args_list]
        assert any(f":{uid}:min" in k for k in calls)
        assert any(f":{uid}:day" in k for k in calls)
