"""
CAMS Gemini Client — Implementation of LLMClient using Google GenAI SDK.
Includes structured quota error extraction and sensitive credential scrubbing.
"""
import asyncio
import logging
import re
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional

from app.services.ai_tutor.provider import get_search_puzzles_tool
from app.services.llm.base import LLMClient, LLMProviderError
from app.services.llm.crypto import sanitize_sensitive_text

logger = logging.getLogger(__name__)


def parse_gemini_quota_details(err_msg: str) -> tuple[Optional[str], Optional[str], str]:
    """
    Extract quotaMetric, quotaId, and determine if quota is per-minute or per-day.
    Returns: (quota_metric, quota_id, quota_period)
    """
    metric = None
    quota_id = None
    period = "unknown"

    metric_match = re.search(r"quotaMetric['\"]?\s*:\s*['\"]?([a-zA-Z0-9_\-\.]+)", err_msg)
    if metric_match:
        metric = metric_match.group(1)

    id_match = re.search(r"quotaId['\"]?\s*:\s*['\"]?([a-zA-Z0-9_\-\.]+)", err_msg)
    if id_match:
        quota_id = id_match.group(1)

    lower = err_msg.lower()
    if "per-minute" in lower or "per_minute" in lower or "requests per minute" in lower or "tpm" in lower or "rpm" in lower:
        period = "minute"
    elif "per-day" in lower or "per_day" in lower or "requests per day" in lower or "rpd" in lower:
        period = "day"
    elif metric:
        if "minute" in metric.lower():
            period = "minute"
        elif "day" in metric.lower():
            period = "day"

    return metric, quota_id, period


class GeminiClient(LLMClient):
    """Google Gemini LLM implementation with streaming and tool support."""

    def __init__(self, api_key: str, default_model: str = "gemini-3.8-flash"):
        self.api_key = api_key.strip() if api_key else ""
        self.default_model = default_model
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise LLMProviderError(
                    "Chưa có API key cho Google Gemini.",
                    code="auth",
                    retryable=False,
                    provider_name="Gemini",
                )
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Google GenAI Client: %s", type(e).__name__)
                raise LLMProviderError(
                    "Không thể khởi tạo kết nối đến Google Gemini API.",
                    code="auth",
                    retryable=False,
                    provider_name="Gemini",
                )
        return self._client

    async def stream_chat(
        self,
        system_instruction: str,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_output_tokens: int = 1500,
        tool_handler: Optional[Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]] = None,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        target_model = model or self.default_model

        try:
            from google.genai import types

            contents = []
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg.get("content", ""))]
                    )
                )

            tools = [get_search_puzzles_tool()] if tool_handler else None

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
                tools=tools,
            )

            # Check for tool calling up to 2 iterations
            max_iterations = 2
            current_iteration = 0

            while current_iteration < max_iterations:
                current_iteration += 1

                if tools:
                    response = await client.aio.models.generate_content(
                        model=target_model,
                        contents=contents,
                        config=config,
                    )

                    if response.function_calls and tool_handler:
                        call = response.function_calls[0]
                        logger.info("Gemini requested tool call: %s(args=%s)", call.name, call.args)

                        tool_result = await tool_handler(call.name, dict(call.args or {}))

                        if response.candidates and response.candidates[0].content:
                            contents.append(response.candidates[0].content)

                        contents.append(
                            types.Content(
                                role="tool",
                                parts=[
                                    types.Part.from_function_response(
                                        name=call.name,
                                        response=tool_result,
                                    )
                                ],
                            )
                        )
                        config.tools = None
                        tools = None
                        continue
                    else:
                        if response.text:
                            chunk_size = 20
                            for i in range(0, len(response.text), chunk_size):
                                yield response.text[i : i + chunk_size]
                                await asyncio.sleep(0.01)
                        return
                else:
                    response_stream = await client.aio.models.generate_content_stream(
                        model=target_model,
                        contents=contents,
                        config=config,
                    )
                    async for chunk in response_stream:
                        if chunk and chunk.text:
                            yield chunk.text
                    return

        except asyncio.TimeoutError:
            logger.warning("Gemini API call timed out.")
            raise LLMProviderError(
                "Yêu cầu gửi đến AI bị quá thời gian chờ (timeout). Vui lòng thử lại.",
                code="timeout",
                retryable=True,
                provider_name="Gemini",
            )
        except LLMProviderError:
            raise
        except Exception as e:
            err_type = type(e).__name__
            raw_err = str(e)
            safe_err = sanitize_sensitive_text(raw_err, known_secrets=[self.api_key])
            lower = safe_err.lower()

            metric, q_id, q_period = None, None, "unknown"
            if "429" in safe_err or "resource_exhausted" in lower or "quota" in lower:
                metric, q_id, q_period = parse_gemini_quota_details(safe_err)
                logger.warning(
                    "Gemini 429 Quota Exceeded [period=%s, metric=%s, id=%s]: %s",
                    q_period,
                    metric or "unknown",
                    q_id or "unknown",
                    safe_err[:300],
                )
                raise LLMProviderError(
                    "Hệ thống AI đang tạm thời vượt hạn ngạch (quota) của dịch vụ. Vui lòng thử lại sau vài phút.",
                    code="quota",
                    retryable=True,
                    quota_metric=metric,
                    quota_id=q_id,
                    quota_period=q_period,
                    provider_name="Gemini",
                    raw_error=safe_err,
                )

            if "503" in safe_err or "unavailable" in lower or "overloaded" in lower or "high demand" in lower:
                logger.warning("Gemini 503 Overloaded: %s", safe_err[:300])
                raise LLMProviderError(
                    "Hệ thống AI đang quá tải do lượng truy cập cao. Vui lòng thử lại sau vài giây.",
                    code="overloaded",
                    retryable=True,
                    provider_name="Gemini",
                    raw_error=safe_err,
                )

            if "api_key_invalid" in lower or ("400" in safe_err and "key" in lower) or "401" in safe_err or "403" in safe_err:
                logger.error("Gemini Auth Error: %s", safe_err[:300])
                raise LLMProviderError(
                    "Khóa API dịch vụ Gemini chưa hợp lệ hoặc chưa được kích hoạt.",
                    code="auth",
                    retryable=False,
                    provider_name="Gemini",
                    raw_error=safe_err,
                )

            logger.error("Gemini Unexpected Error (%s): %s", err_type, safe_err[:300])
            raise LLMProviderError(
                "Dịch vụ AI đang gặp sự cố kết nối. Vui lòng thử lại sau.",
                code="other",
                retryable=False,
                provider_name="Gemini",
                raw_error=safe_err,
            )
