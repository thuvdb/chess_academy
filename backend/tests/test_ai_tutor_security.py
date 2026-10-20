"""
Unit tests for AI Tutor Security, Prompt Guardrails, Rate Limiting, and Mock Provider.
"""
import uuid
import pytest
from app.core.redis import normalize_query, hash_query
from app.services.ai_tutor.prompt import AI_TUTOR_SYSTEM_PROMPT
from app.services.ai_tutor.provider import MockLLMProvider


def test_normalize_query():
    """Verify query normalization strips punctuation, whitespace, and case."""
    q1 = "  Khai cuộc Ý đi như thế nào??? "
    q2 = "khai cuộc ý đi như thế nào"
    assert normalize_query(q1) == normalize_query(q2)
    assert hash_query(normalize_query(q1)) == hash_query(normalize_query(q2))


def test_system_prompt_guardrails():
    """Verify system prompt contains essential guardrails against off-topic queries and prompt extraction."""
    prompt_lower = AI_TUTOR_SYSTEM_PROMPT.lower()
    
    # Must enforce chess-only scope
    assert "chỉ trả lời về cờ vua" in prompt_lower or "cờ vua" in prompt_lower
    # Must enforce polite refusal for off-topic questions
    assert "từ chối" in prompt_lower
    # Must forbid prompt leaking & role switching
    assert "system prompt" in prompt_lower or "vai trò" in prompt_lower
    # Must instruct board format
    assert "<board>" in AI_TUTOR_SYSTEM_PROMPT
    assert "moves" in AI_TUTOR_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_mock_llm_provider_chess_streaming():
    """Verify MockLLMProvider streams chess response with board markup for Italian Game."""
    provider = MockLLMProvider()
    chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "Khai cuộc Ý là gì?"}],
        system_instruction=AI_TUTOR_SYSTEM_PROMPT,
    ):
        chunks.append(chunk)

    full_response = "".join(chunks)
    assert "Khai cuộc Ý" in full_response
    assert "<board>" in full_response
    assert "Bc4" in full_response


@pytest.mark.asyncio
async def test_mock_llm_provider_off_topic_rejection():
    """Verify MockLLMProvider politely rejects off-topic non-chess questions."""
    provider = MockLLMProvider()
    chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "Thời tiết hôm nay thế nào?"}],
        system_instruction=AI_TUTOR_SYSTEM_PROMPT,
    ):
        chunks.append(chunk)

    full_response = "".join(chunks)
    assert "Huấn luyện viên Cờ vua" in full_response
    assert "chỉ có thể hỗ trợ con về các chủ đề cờ vua" in full_response
