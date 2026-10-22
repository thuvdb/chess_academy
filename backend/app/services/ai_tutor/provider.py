"""
CAMS AI Tutor — LLM Provider Abstraction.
Supports Google Gemini via google-genai SDK and Mock provider for testing.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Awaitable, Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_search_puzzles_tool():
    """Build the FunctionDeclaration for Gemini tool calling to search Puzzle Bank."""
    from google.genai import types

    func_decl = types.FunctionDeclaration(
        name="search_puzzles",
        description=(
            "Tìm kiếm bài tập cờ thế thực tế đã được duyệt từ kho Puzzle Bank của Học viện CAMS. "
            "Gọi tool này khi học viên xin bài tập, muốn giải cờ thế hoặc luyện tập chiến thuật."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "theme": {
                    "type": "string",
                    "description": "Chủ đề bài tập (ví dụ: 'ghim', 'đòn đôi', 'fork', 'chiếu hết', 'mate_in_1', 'mate_in_2', 'tàn cuộc', 'khai cuộc').",
                },
                "level": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "Cấp độ khó của bài tập (mặc định 'easy').",
                },
                "limit": {
                    "type": "integer",
                    "description": "Số lượng bài tập cần tìm (tối đa 3).",
                },
            },
            "required": ["theme"],
        },
    )
    return types.Tool(function_declarations=[func_decl])


class AIProviderError(Exception):
    """Safe exception for AI provider failures with structured error code and retry eligibility."""
    def __init__(
        self,
        message: str = "Dịch vụ AI đang gián đoạn hoặc quá tải. Vui lòng thử lại sau.",
        code: str = "other",
        retryable: bool = False,
    ):
        self.message = message
        self.code = code  # "overloaded" | "quota" | "timeout" | "auth" | "other"
        self.retryable = retryable
        super().__init__(self.message)


def classify_gemini_error(err_msg: str, err_type: str = "") -> tuple[str, str, bool]:
    """
    Classify Gemini API errors into user-friendly message, structured error code, and retry eligibility.
    Codes: 'overloaded' | 'quota' | 'timeout' | 'auth' | 'other'
    """
    lower = err_msg.lower()
    if (
        "503" in err_msg
        or "unavailable" in lower
        or "high demand" in lower
        or "overloaded" in lower
        or "experiencing high demand" in lower
    ):
        return (
            "Hệ thống AI đang quá tải do lượng truy cập cao. Vui lòng thử lại sau vài giây.",
            "overloaded",
            True,
        )
    if "429" in err_msg or "resource_exhausted" in lower or "quota" in lower:
        return (
            "Hệ thống AI đang tạm thời vượt hạn ngạch (quota) của dịch vụ. Vui lòng thử lại sau vài phút.",
            "quota",
            True,
        )
    if "timeout" in lower or "deadline" in lower or err_type == "TimeoutError":
        return (
            "Yêu cầu gửi đến AI bị quá thời gian chờ (timeout). Vui lòng thử lại.",
            "timeout",
            True,
        )
    if "api_key_invalid" in lower or ("400" in err_msg and "key" in lower):
        return (
            "Khóa API dịch vụ AI chưa hợp lệ hoặc chưa được kích hoạt.",
            "auth",
            False,
        )
    return (
        "Dịch vụ AI đang gặp sự cố kết nối. Vui lòng thử lại sau.",
        "other",
        False,
    )


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        system_instruction: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        tool_handler: Optional[Callable[[str, dict], Awaitable[dict]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chunks of response text from the LLM."""
        pass


class GeminiLLMProvider(LLMProvider):
    """Google Gemini LLM implementation using the modern google-genai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-3.8-flash"):
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
        tool_handler: Optional[Callable[[str, dict], Awaitable[dict]]] = None,
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

            tools = [get_search_puzzles_tool()] if tool_handler else None

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_tokens,
                temperature=temperature,
                tools=tools,
            )

            # Check for tool calling up to 2 iterations
            max_iterations = 2
            current_iteration = 0

            while current_iteration < max_iterations:
                current_iteration += 1

                # If tools are configured, test if model invokes a function call
                if tools:
                    response = await client.aio.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=config,
                    )

                    if response.function_calls and tool_handler:
                        call = response.function_calls[0]
                        logger.info("LLM requested tool call: %s(args=%s)", call.name, call.args)

                        # Execute tool handler
                        tool_result = await tool_handler(call.name, dict(call.args or {}))

                        # Append model function call turn and tool response turn
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
                        # Disable tools for subsequent generation turn so it produces final message
                        config.tools = None
                        tools = None
                        continue
                    else:
                        # No tool called: yield text response from candidate
                        if response.text:
                            chunk_size = 20
                            for i in range(0, len(response.text), chunk_size):
                                yield response.text[i : i + chunk_size]
                                await asyncio.sleep(0.01)
                        return
                else:
                    # Stream final text response
                    response_stream = await client.aio.models.generate_content_stream(
                        model=self.model,
                        contents=contents,
                        config=config,
                    )
                    async for chunk in response_stream:
                        if chunk and chunk.text:
                            yield chunk.text
                    return

        except asyncio.TimeoutError:
            logger.warning("Gemini API call timed out after configured threshold.")
            raise AIProviderError(
                "Yêu cầu gửi đến AI bị quá thời gian chờ (timeout). Vui lòng thử lại.",
                code="timeout",
                retryable=True,
            )
        except AIProviderError:
            raise
        except Exception as e:
            err_type = type(e).__name__
            err_msg = str(e)
            # Ensure API Key is NEVER printed in logs
            safe_err = err_msg.replace(self.api_key, "[REDACTED_API_KEY]") if self.api_key else err_msg
            logger.error("Gemini API streaming error (%s): %s", err_type, safe_err)

            msg, code, retryable = classify_gemini_error(safe_err, err_type=err_type)
            raise AIProviderError(msg, code=code, retryable=retryable)


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
        tool_handler: Optional[Callable[[str, dict], Awaitable[dict]]] = None,
    ) -> AsyncGenerator[str, None]:
        last_message = messages[-1].get("content", "").lower() if messages else ""

        if self.canned_response:
            response = self.canned_response
        elif any(k in last_message for k in ["bài tập", "thế cờ", "puzzle", "đòn ghim", "đòn đôi", "luyện tập"]) and tool_handler:
            # Simulate tool call to search_puzzles
            theme = "ghim" if "ghim" in last_message else ("đòn đôi" if "đôi" in last_message else "chiến thuật")
            tool_res = await tool_handler("search_puzzles", {"theme": theme, "limit": 2})
            count = tool_res.get("puzzles_found", 0)
            if count > 0:
                response = (
                    f"Thầy đã tìm thấy {count} thế cờ phù hợp về chủ đề {theme} từ kho Puzzle Bank của Học viện CAMS cho con đây! "
                    "Con hãy quan sát kĩ bàn cờ bên dưới và đi thử nước tối ưu nhất nhé."
                )
            else:
                response = (
                    f"Hiện tại trong kho bài tập của Học viện chưa có bài tập về chủ đề '{theme}'. "
                    "Con có thể thử luyện tập các chủ đề phổ biến khác như: đòn ghim, đòn đôi, hoặc chiếu hết trong 1-2 nước nhé!"
                )
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
