"""
Unit tests for LLM Provider Abstraction, OpenAI SSE parser, Quota analysis, and Fallback.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm.base import LLMClient, LLMProviderError
from app.services.llm.gemini_client import parse_gemini_quota_details
from app.services.llm.manager import stream_chat_resilient
from app.services.llm.openai_compat_client import OpenAICompatClient


def test_parse_gemini_quota_details():
    err1 = "ResourceExhausted: 429 Quota exceeded for quotaMetric: 'generate-content-requests-per-minute' and quotaId: 'gemini-flash-tier1'"
    metric, q_id, period = parse_gemini_quota_details(err1)
    assert metric == "generate-content-requests-per-minute"
    assert q_id == "gemini-flash-tier1"
    assert period == "minute"

    err2 = "429 Daily limit exceeded. Please wait 24 hours. quotaMetric: 'tokens-per-day'"
    metric2, q_id2, period2 = parse_gemini_quota_details(err2)
    assert period2 == "day"


@pytest.mark.asyncio
async def test_openai_compat_sse_streaming():
    # Mock httpx response stream
    mock_sse_lines = [
        'data: {"choices": [{"delta": {"content": "Xin "}}]}',
        'data: {"choices": [{"delta": {"content": "chào "}}]}',
        'data: {"choices": [{"delta": {"content": "học viên!"}}]}',
        'data: [DONE]',
    ]

    class FakeResponse:
        status_code = 200

        async def aiter_lines(self):
            for line in mock_sse_lines:
                yield line

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    client = OpenAICompatClient(
        base_url="https://mock.api/v1",
        api_key="sk-testkey123456789",
        default_model="gpt-4o-mini",
    )

    with patch("httpx.AsyncClient.stream", return_value=FakeResponse()):
        chunks = []
        async for chunk in client.stream_chat(
            system_instruction="You are a tutor",
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o-mini",
        ):
            chunks.append(chunk)

        assert "".join(chunks) == "Xin chào học viên!"


@pytest.mark.asyncio
async def test_openai_compat_error_handling_sanitizes_key():
    client = OpenAICompatClient(
        base_url="https://mock.api/v1",
        api_key="sk-supersecret1234567890",
    )

    class FakeErrorResponse:
        status_code = 429

        async def aread(self):
            return b'{"error": {"message": "Rate limit exceeded for sk-supersecret1234567890"}}'

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient.stream", return_value=FakeErrorResponse()):
        with pytest.raises(LLMProviderError) as exc_info:
            async for _ in client.stream_chat(
                system_instruction="",
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o-mini",
            ):
                pass

        err = exc_info.value
        assert err.code == "quota"
        assert err.retryable is True
        assert "sk-supersecret1234567890" not in (err.raw_error or "")


@pytest.mark.asyncio
async def test_stream_chat_fallback_mechanism():
    """
    Test that when primary provider repeatedly raises retryable LLMProviderError,
    stream_chat_resilient automatically transitions to fallback provider.
    """
    mock_config = {
        "settings": {
            "default_model": "gemini-3.8-flash",
            "fallback_model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_output_tokens": 1000,
            "request_timeout_seconds": 10,
            "max_retries": 2,
        },
        "default_provider": {
            "name": "Failing Primary",
            "type": "gemini",
            "api_key_encrypted": "test_enc_key1",
            "enabled": True,
        },
        "fallback_provider": {
            "name": "Working Fallback",
            "type": "openai_compatible",
            "base_url": "https://fallback.api/v1",
            "api_key_encrypted": "test_enc_key2",
            "enabled": True,
        },
    }

    class MockFailingClient(LLMClient):
        async def stream_chat(self, *args, **kwargs):
            raise LLMProviderError("Primary 429 Overload", code="overloaded", retryable=True)
            yield ""

    class MockFallbackClient(LLMClient):
        async def stream_chat(self, *args, **kwargs):
            yield "Phản hồi từ "
            yield "fallback provider thành công!"

    def mock_instantiate(prov_dict, timeout_seconds=30.0):
        if prov_dict and prov_dict.get("name") == "Failing Primary":
            return MockFailingClient()
        return MockFallbackClient()

    with patch("app.services.llm.manager.get_active_ai_config", AsyncMock(return_value=mock_config)):
        with patch("app.services.llm.manager.instantiate_llm_client", side_effect=mock_instantiate):
            with patch("asyncio.sleep", AsyncMock()):  # Speed up backoff delay in test
                collected = []
                async for chunk in stream_chat_resilient(
                    system_instruction="test",
                    messages=[{"role": "user", "content": "hi"}],
                ):
                    collected.append(chunk)

                assert "".join(collected) == "Phản hồi từ fallback provider thành công!"
