"""
CAMS OpenAI Compatible Client — Implementation of LLMClient for OpenAI-compatible APIs
(e.g., AgentRouter, OpenRouter, DeepSeek, Local Ollama, vLLM).
"""
import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional

import httpx

from app.services.llm.base import LLMClient, LLMProviderError
from app.services.llm.crypto import sanitize_sensitive_text

logger = logging.getLogger(__name__)


class OpenAICompatClient(LLMClient):
    """Client for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        default_model: str = "gpt-4o-mini",
        timeout_seconds: float = 30.0,
    ):
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds

    def _normalize_chat_url(self) -> str:
        """Ensure endpoint is correctly formed: {base_url}/chat/completions."""
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        return url

    async def stream_chat(
        self,
        system_instruction: str,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_output_tokens: int = 1500,
        tool_handler: Optional[Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]] = None,
    ) -> AsyncGenerator[str, None]:
        url = self._normalize_chat_url()
        target_model = model or self.default_model

        # Build payload
        formatted_messages = []
        if system_instruction:
            formatted_messages.append({"role": "system", "content": system_instruction})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_messages.append({"role": role, "content": content})

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": formatted_messages,
            "temperature": temperature,
            "stream": True,
        }

        # Groq and modern reasoning models reject max_tokens and require max_completion_tokens
        is_groq = "groq.com" in self.base_url.lower()
        is_reasoning = any(x in target_model.lower() for x in ["gpt-oss", "o1", "o3", "r1"])
        if is_groq or is_reasoning:
            payload["max_completion_tokens"] = max_output_tokens
            if is_groq and "gpt-oss" in target_model.lower():
                payload["reasoning_format"] = "raw"
        else:
            payload["max_tokens"] = max_output_tokens

        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = httpx.Timeout(self.timeout_seconds, connect=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        raw_err_str = error_body.decode("utf-8", errors="replace")
                        safe_err = sanitize_sensitive_text(raw_err_str, known_secrets=[self.api_key])
                        status = response.status_code

                        logger.warning(
                            "OpenAI-compat API error [status=%d]: %s",
                            status,
                            safe_err[:300],
                        )

                        if status == 429:
                            lower = safe_err.lower()
                            period = "minute" if ("minute" in lower or "rpm" in lower or "tpm" in lower) else (
                                "day" if ("day" in lower or "rpd" in lower or "daily" in lower) else "unknown"
                            )
                            raise LLMProviderError(
                                "Hệ thống AI đang tạm thời vượt hạn ngạch (quota) của dịch vụ. Vui lòng thử lại sau vài phút.",
                                code="quota",
                                retryable=True,
                                quota_period=period,
                                provider_name="OpenAICompat",
                                raw_error=safe_err,
                            )
                        elif status in (500, 502, 503, 504):
                            raise LLMProviderError(
                                "Dịch vụ AI đối tác đang gián đoạn hoặc quá tải. Vui lòng thử lại sau.",
                                code="overloaded",
                                retryable=True,
                                provider_name="OpenAICompat",
                                raw_error=safe_err,
                            )
                        elif status in (401, 403):
                            raise LLMProviderError(
                                "Khóa API của nhà cung cấp AI chưa hợp lệ hoặc bị từ chối truy cập.",
                                code="auth",
                                retryable=False,
                                provider_name="OpenAICompat",
                                raw_error=safe_err,
                            )
                        else:
                            raise LLMProviderError(
                                f"Lỗi từ nhà cung cấp AI ({status}). Vui lòng thử lại sau.",
                                code="other",
                                retryable=False,
                                provider_name="OpenAICompat",
                                raw_error=safe_err,
                            )

                    # Process SSE Stream line-by-line
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data:"):
                            continue

                        data_content = line[5:].strip()
                        if data_content == "[DONE]":
                            break

                        try:
                            chunk_json = json.loads(data_content)
                            choices = chunk_json.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                text = delta.get("content") or delta.get("reasoning") or delta.get("reasoning_content") or ""
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException:
            logger.warning("OpenAI-compat API request timed out after %.1fs", self.timeout_seconds)
            raise LLMProviderError(
                "Yêu cầu gửi đến AI bị quá thời gian chờ (timeout). Vui lòng thử lại.",
                code="timeout",
                retryable=True,
                provider_name="OpenAICompat",
            )
        except LLMProviderError:
            raise
        except Exception as e:
            raw_err = str(e)
            safe_err = sanitize_sensitive_text(raw_err, known_secrets=[self.api_key])
            logger.error("OpenAI-compat communication failure: %s", safe_err[:300])
            raise LLMProviderError(
                "Không thể kết nối đến nhà cung cấp AI. Vui lòng kiểm tra cấu hình mạng/URL.",
                code="other",
                retryable=False,
                provider_name="OpenAICompat",
                raw_error=safe_err,
            )
