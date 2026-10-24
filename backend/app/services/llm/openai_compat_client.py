"""
CAMS OpenAI Compatible Client — Implementation of LLMClient for OpenAI-compatible APIs
(e.g., AgentRouter, OpenRouter, DeepSeek, Groq, Local Ollama, vLLM).
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
        reasoning_effort: Optional[str] = None,
    ):
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds
        effort_clean = reasoning_effort.strip().lower() if isinstance(reasoning_effort, str) else None
        self.reasoning_effort = effort_clean if effort_clean in ("low", "medium", "high") else None

    def _normalize_chat_url(self) -> str:
        """Ensure endpoint is correctly formed: {base_url}/chat/completions."""
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        return url

    @staticmethod
    def _sanitize_payload_for_logging(payload: dict[str, Any]) -> dict[str, Any]:
        """Strip message content text and credentials from request payload for safe 400 debugging logs."""
        sanitized = {}
        for k, v in payload.items():
            if k == "messages" and isinstance(v, list):
                sanitized["messages"] = [
                    {
                        "role": m.get("role") if isinstance(m, dict) else "unknown",
                        "content_length": len(str(m.get("content", ""))) if isinstance(m, dict) else 0,
                    }
                    for m in v
                ]
            elif "key" in k.lower() or "secret" in k.lower() or "token" in k.lower() and k not in ("max_tokens", "max_completion_tokens"):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = v
        return sanitized

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
            formatted_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": formatted_messages,
            "temperature": temperature,
            "stream": True,
        }

        # OpenAI o1/o3 reject max_tokens and require max_completion_tokens.
        # Other providers (Groq, DeepSeek, etc.) accept max_tokens directly.
        is_o_series = any(x in target_model.lower() for x in ["o1", "o3"])
        if is_o_series:
            payload["max_completion_tokens"] = max_output_tokens
        else:
            payload["max_tokens"] = max_output_tokens

        # Only send reasoning_effort if explicitly selected
        if self.reasoning_effort in ("low", "medium", "high"):
            payload["reasoning_effort"] = self.reasoning_effort

        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = httpx.Timeout(self.timeout_seconds, connect=10.0)
        attempt_payload = dict(payload)
        retried_without_reasoning = False

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                while True:
                    async with client.stream("POST", url, json=attempt_payload, headers=headers) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            raw_err_str = error_body.decode("utf-8", errors="replace")
                            safe_err = sanitize_sensitive_text(raw_err_str, known_secrets=[self.api_key])
                            status = response.status_code

                            # 400 Bad Request logging & automatic retry if reasoning_effort rejected
                            if status == 400:
                                sanitized_body = self._sanitize_payload_for_logging(attempt_payload)
                                logger.warning(
                                    "OpenAI-compat API 400 Bad Request. Sanitized payload: %s | Error: %s",
                                    sanitized_body,
                                    safe_err[:300],
                                )
                                if "reasoning_effort" in attempt_payload and not retried_without_reasoning:
                                    logger.warning(
                                        "Provider returned 400 with reasoning_effort=%s. Automatically retrying once without reasoning_effort...",
                                        attempt_payload.get("reasoning_effort"),
                                    )
                                    attempt_payload.pop("reasoning_effort", None)
                                    retried_without_reasoning = True
                                    continue

                            err_detail = ""
                            try:
                                parsed = json.loads(safe_err)
                                err_detail = (
                                    parsed.get("error", {}).get("message")
                                    if isinstance(parsed.get("error"), dict)
                                    else (parsed.get("error") or parsed.get("message") or "")
                                )
                            except Exception:
                                err_detail = safe_err[:150]

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
                                    f"Hệ thống AI đang tạm thời vượt hạn ngạch (quota) của dịch vụ ({period}): {err_detail or 'Vui lòng thử lại sau vài phút.'}",
                                    code="quota",
                                    retryable=True,
                                    quota_period=period,
                                    provider_name="OpenAICompat",
                                    raw_error=safe_err,
                                )
                            elif status in (500, 502, 503, 504):
                                raise LLMProviderError(
                                    f"Dịch vụ AI đối tác đang gián đoạn hoặc quá tải ({status}): {err_detail}",
                                    code="overloaded",
                                    retryable=True,
                                    provider_name="OpenAICompat",
                                    raw_error=safe_err,
                                )
                            elif status in (401, 403):
                                raise LLMProviderError(
                                    f"Khóa API chưa hợp lệ hoặc bị từ chối truy cập ({status}): {err_detail}",
                                    code="auth",
                                    retryable=False,
                                    provider_name="OpenAICompat",
                                    raw_error=safe_err,
                                )
                            elif status == 404:
                                detail_str = f": {err_detail}" if err_detail else f" (Model '{target_model}' không tồn tại hoặc sai URL)"
                                raise LLMProviderError(
                                    f"Lỗi 404 từ nhà cung cấp AI{detail_str}",
                                    code="not_found",
                                    retryable=False,
                                    provider_name="OpenAICompat",
                                    raw_error=safe_err,
                                )
                            else:
                                detail_str = f": {err_detail}" if err_detail else ""
                                raise LLMProviderError(
                                    f"Lỗi từ nhà cung cấp AI ({status}){detail_str}",
                                    code="other",
                                    retryable=False,
                                    provider_name="OpenAICompat",
                                    raw_error=safe_err,
                                )

                        content_emitted = False
                        last_finish_reason: Optional[str] = None

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
                                    choice = choices[0]
                                    finish_reason = choice.get("finish_reason")
                                    if finish_reason:
                                        last_finish_reason = finish_reason

                                    delta = choice.get("delta", {})
                                    # STRICT RULE: ONLY extract content (never reasoning or reasoning_content)
                                    content_chunk = delta.get("content")
                                    text = content_chunk if isinstance(content_chunk, str) else ""
                                    if text:
                                        content_emitted = True
                                        yield text

                                    if finish_reason == "length" and not content_emitted:
                                        raise LLMProviderError(
                                            "Câu trả lời bị cắt do giới hạn token (mô hình đã dùng hết số token quy định trong quá trình suy luận). Vui lòng tăng Max Tokens trong Cấu hình AI để nhận câu trả lời.",
                                            code="length_limit",
                                            retryable=False,
                                            provider_name="OpenAICompat",
                                        )
                            except json.JSONDecodeError:
                                continue

                        # End of stream check for empty reasoning-exhausted responses
                        if last_finish_reason == "length" and not content_emitted:
                            raise LLMProviderError(
                                "Câu trả lời bị cắt do giới hạn token (mô hình đã dùng hết số token quy định trong quá trình suy luận). Vui lòng tăng Max Tokens trong Cấu hình AI để nhận câu trả lời.",
                                code="length_limit",
                                retryable=False,
                                provider_name="OpenAICompat",
                            )

                        break

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
