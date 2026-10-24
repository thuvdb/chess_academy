import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.schemas.ai_settings import AIProviderBase, AIProviderUpdate, AIProviderOut
from app.models.ai_settings import AIProvider
from app.services.llm.openai_compat_client import OpenAICompatClient
from app.services.llm.base import LLMProviderError


def test_schema_reasoning_effort_validation():
    # Valid values
    p1 = AIProviderBase(name="Groq", type="openai_compatible", reasoning_effort="low")
    assert p1.reasoning_effort == "low"

    p2 = AIProviderBase(name="Groq", type="openai_compatible", reasoning_effort="Medium ")
    assert p2.reasoning_effort == "medium"

    p3 = AIProviderBase(name="Groq", type="openai_compatible", reasoning_effort="")
    assert p3.reasoning_effort is None

    p4 = AIProviderBase(name="Groq", type="openai_compatible", reasoning_effort=None)
    assert p4.reasoning_effort is None

    # Invalid value
    with pytest.raises(ValueError):
        AIProviderBase(name="Groq", type="openai_compatible", reasoning_effort="super_high")

    # Update schema
    up = AIProviderUpdate(reasoning_effort="high")
    assert up.reasoning_effort == "high"


def test_model_has_reasoning_effort_column():
    provider = AIProvider(
        name="Groq Test",
        type="openai_compatible",
        reasoning_effort="low",
    )
    assert hasattr(provider, "reasoning_effort")
    assert provider.reasoning_effort == "low"


def test_sanitize_payload_for_logging():
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": "You are a master chess tutor"},
            {"role": "user", "content": "How do I play the Sicilian Defense?"},
        ],
        "api_key": "gsk_super_secret_12345678",
        "max_tokens": 200,
        "temperature": 0.7,
        "reasoning_effort": "low",
    }
    sanitized = OpenAICompatClient._sanitize_payload_for_logging(payload)
    assert sanitized["model"] == "openai/gpt-oss-20b"
    assert sanitized["api_key"] == "***REDACTED***"
    assert sanitized["max_tokens"] == 200
    assert sanitized["reasoning_effort"] == "low"

    # Verify message content text is strictly removed, only length preserved
    assert len(sanitized["messages"]) == 2
    assert sanitized["messages"][0]["role"] == "system"
    assert sanitized["messages"][0]["content_length"] == len("You are a master chess tutor")
    assert "content" not in sanitized["messages"][0]
    assert sanitized["messages"][1]["role"] == "user"
    assert sanitized["messages"][1]["content_length"] == len("How do I play the Sicilian Defense?")
    assert "content" not in sanitized["messages"][1]


@pytest.mark.asyncio
async def test_stream_chat_filters_reasoning_and_keeps_only_content():
    """Verify that reasoning / reasoning_content chunks are strictly ignored."""
    client = OpenAICompatClient(
        base_url="https://api.groq.com/openai/v1",
        api_key="test_key",
        default_model="openai/gpt-oss-20b",
    )

    sse_lines = [
        # Chunk 1: internal reasoning thought
        'data: {"choices": [{"delta": {"reasoning": "Let me think about e4..."}, "finish_reason": null}]}\n',
        # Chunk 2: another reasoning field style
        'data: {"choices": [{"delta": {"reasoning_content": "Evaluation is +0.3."}, "finish_reason": null}]}\n',
        # Chunk 3: actual visible content for user
        'data: {"choices": [{"delta": {"content": "Chào bạn! "}, "finish_reason": null}]}\n',
        # Chunk 4: actual visible content chunk 2
        'data: {"choices": [{"delta": {"content": "Tôi là Huấn luyện viên Cờ vua."}, "finish_reason": "stop"}]}\n',
        'data: [DONE]\n',
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200

    async def aiter_lines():
        for line in sse_lines:
            yield line

    mock_response.aiter_lines = aiter_lines

    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response

        collected = []
        async for chunk in client.stream_chat(
            system_instruction="",
            messages=[{"role": "user", "content": "hi"}],
            model="openai/gpt-oss-20b",
            max_output_tokens=200,
        ):
            collected.append(chunk)

        result_text = "".join(collected)
        # MUST contain user content
        assert result_text == "Chào bạn! Tôi là Huấn luyện viên Cờ vua."
        # MUST NOT contain reasoning tokens
        assert "Let me think" not in result_text
        assert "Evaluation" not in result_text


@pytest.mark.asyncio
async def test_finish_reason_length_with_empty_content_raises_friendly_error():
    """Verify that when a reasoning model burns all tokens in reasoning phase and yields no content, user gets a friendly error."""
    client = OpenAICompatClient(
        base_url="https://api.groq.com/openai/v1",
        api_key="test_key",
        default_model="openai/gpt-oss-20b",
    )

    sse_lines = [
        # All tokens exhausted during internal reasoning, finish_reason = length
        'data: {"choices": [{"delta": {"reasoning": "Thinking deeply..."}, "finish_reason": null}]}\n',
        'data: {"choices": [{"delta": {}, "finish_reason": "length"}]}\n',
        'data: [DONE]\n',
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200

    async def aiter_lines():
        for line in sse_lines:
            yield line

    mock_response.aiter_lines = aiter_lines

    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response

        with pytest.raises(LLMProviderError) as exc_info:
            async for _ in client.stream_chat(
                system_instruction="",
                messages=[{"role": "user", "content": "Solve this puzzle"}],
                model="openai/gpt-oss-20b",
                max_output_tokens=50,
            ):
                pass

        err = exc_info.value
        assert err.code == "length_limit"
        assert err.retryable is False
        assert "câu trả lời bị cắt do giới hạn token" in str(err).lower()
        assert "tăng max tokens" in str(err).lower()


@pytest.mark.asyncio
async def test_retry_on_400_without_reasoning_effort():
    """Verify that if provider returns 400 Bad Request with reasoning_effort, it retries without reasoning_effort."""
    client = OpenAICompatClient(
        base_url="https://api.groq.com/openai/v1",
        api_key="test_key",
        default_model="openai/gpt-oss-20b",
        reasoning_effort="low",
    )

    resp_400 = MagicMock()
    resp_400.status_code = 400
    resp_400.aread = AsyncMock(return_value=b'{"error": {"message": "Unknown parameter: reasoning_effort"}}')

    resp_200 = MagicMock()
    resp_200.status_code = 200

    async def aiter_lines():
        yield 'data: {"choices": [{"delta": {"content": "Xin chao!"}, "finish_reason": "stop"}]}\n'
        yield 'data: [DONE]\n'

    resp_200.aiter_lines = aiter_lines

    call_count = 0
    sent_payloads = []

    def mock_stream_call(method, url, json=None, headers=None):
        nonlocal call_count
        call_count += 1
        sent_payloads.append(dict(json))

        mock_ctx = MagicMock()
        if call_count == 1:
            mock_ctx.__aenter__ = AsyncMock(return_value=resp_400)
        else:
            mock_ctx.__aenter__ = AsyncMock(return_value=resp_200)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        return mock_ctx

    with patch("httpx.AsyncClient.stream", side_effect=mock_stream_call):
        collected = []
        async for chunk in client.stream_chat(
            system_instruction="",
            messages=[{"role": "user", "content": "hi"}],
            model="openai/gpt-oss-20b",
        ):
            collected.append(chunk)

        assert "".join(collected) == "Xin chao!"
        assert call_count == 2
        # First request contained reasoning_effort
        assert "reasoning_effort" in sent_payloads[0]
        assert sent_payloads[0]["reasoning_effort"] == "low"
        # Second retried request removed reasoning_effort
        assert "reasoning_effort" not in sent_payloads[1]
