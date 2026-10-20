"""
CAMS AI Tutor — LLM Provider Abstraction.
Supports Google Gemini via google-genai SDK and Mock provider for testing.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Safe exception for AI provider failures without leaking sensitive credentials."""
    def __init__(self, message: str = "Dịch vụ AI đang gián đoạn hoặc quá tải. Vui lòng thử lại sau."):
        self.message = message
        super().__init__(self.message)


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        system_instruction: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream chunks of response text from the LLM."""
        pass


class GeminiLLMProvider(LLMProvider):
    """Google Gemini LLM implementation using the modern google-genai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        # Lazy initialization
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Google GenAI Client: %s", type(e).__name__)
                raise AIProviderError("Không thể khởi tạo kết nối đến Google Gemini API.")
        return self._client

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        system_instruction: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
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

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_tokens,
                temperature=temperature,
            )

            response_stream = await client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            )

            async for chunk in response_stream:
                if chunk and chunk.text:
                    yield chunk.text

        except asyncio.TimeoutError:
            logger.warning("Gemini API call timed out after configured threshold.")
            raise AIProviderError("Yêu cầu gửi đến AI bị quá thời gian chờ (timeout). Vui lòng thử lại.")
        except Exception as e:
            err_type = type(e).__name__
            err_msg = str(e)
            # Ensure API Key is NEVER printed in logs
            safe_err = err_msg.replace(self.api_key, "[REDACTED_API_KEY]") if self.api_key else err_msg
            logger.error("Gemini API streaming error (%s): %s", err_type, safe_err)

            if "429" in safe_err or "RESOURCE_EXHAUSTED" in safe_err or "quota" in safe_err.lower():
                raise AIProviderError("Hệ thống AI đang tạm thời vượt hạn ngạch (quota) của dịch vụ. Vui lòng thử lại sau vài phút.")
            if "API_KEY_INVALID" in safe_err or "400" in safe_err and "key" in safe_err.lower():
                raise AIProviderError("Khóa API dịch vụ AI chưa hợp lệ hoặc chưa được kích hoạt.")
            
            raise AIProviderError("Dịch vụ AI đang gặp sự cố kết nối. Vui lòng thử lại sau.")


class MockLLMProvider(LLMProvider):
    """Mock LLM Provider for unit testing and offline development."""

    def __init__(self, canned_response: str | None = None):
        self.canned_response = canned_response

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        system_instruction: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        last_message = messages[-1].get("content", "").lower() if messages else ""

        if self.canned_response:
            response = self.canned_response
        elif any(k in last_message for k in ["khai cuộc ý", "italian game", "minh họa"]):
            response = (
                "Chào con! Khai cuộc Ý (Italian Game) là một trong những khai cuộc kinh điển và rất tốt cho học viên CAMS.\n\n"
                "Khai cuộc này bắt đầu với các nước đi:\n"
                "1. e4 e5\n"
                "2. Nf3 Nc6\n"
                "3. Bc4 Bc5\n\n"
                "Mục tiêu của Trắng là phát triển tượng lên ô c4 nhằm nhắm vào điểm yếu f7 của Đen.\n"
                '<board>{"moves":["e4","e5","Nf3","Nc6","Bc4","Bc5"],"caption":"Khai cuộc Ý: 1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5"}</board>'
            )
        elif any(k in last_message for k in ["thời tiết", "toán", "lập trình", "code", "ai"]):
            response = (
                "Thầy là Huấn luyện viên Cờ vua tại Học viện CAMS, nên thầy chỉ có thể hỗ trợ con về các chủ đề cờ vua thôi nhé! "
                "Con có muốn hỏi thầy về một khai cuộc hay chiến thuật cờ vua nào không?"
            )
        else:
            response = (
                "Thầy đã nhận được câu hỏi của con về cờ vua! Hãy luôn nhớ 3 nguyên tắc khai cuộc quan trọng: "
                "Kiểm soát trung tâm, nhanh chóng phát triển quân nhẹ (Mã, Tượng) và sớm nhập thành bảo vệ Vua nhé."
            )

        # Stream chunk by chunk with minimal delay to simulate streaming
        chunk_size = 15
        for i in range(0, len(response), chunk_size):
            yield response[i : i + chunk_size]
            await asyncio.sleep(0.01)


def get_llm_provider() -> LLMProvider:
    """Factory function returning the configured LLM provider."""
    provider_name = settings.AI_TUTOR_PROVIDER.lower().strip()
    api_key = settings.GEMINI_API_KEY.strip()

    if provider_name == "mock" or not api_key:
        if not api_key:
            logger.info("GEMINI_API_KEY is empty. Falling back to MockLLMProvider.")
        return MockLLMProvider()

    return GeminiLLMProvider(api_key=api_key, model=settings.GEMINI_MODEL)
