"""
CAMS LLM Provider Base Interface and Structured Exceptions.
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional


class LLMProviderError(Exception):
    """Structured exception for LLM provider failures."""

    def __init__(
        self,
        message: str = "Dịch vụ AI đang gián đoạn hoặc quá tải. Vui lòng thử lại sau.",
        code: str = "other",  # "overloaded" | "quota" | "timeout" | "auth" | "other"
        retryable: bool = False,
        quota_metric: Optional[str] = None,
        quota_id: Optional[str] = None,
        quota_period: Optional[str] = None,  # "minute" | "day" | "unknown"
        provider_name: Optional[str] = None,
        raw_error: Optional[str] = None,
    ):
        self.message = message
        self.code = code
        self.retryable = retryable
        self.quota_metric = quota_metric
        self.quota_id = quota_id
        self.quota_period = quota_period
        self.provider_name = provider_name
        self.raw_error = raw_error
        super().__init__(self.message)


class LLMClient(ABC):
    """Abstract base class for all LLM client implementations."""

    @abstractmethod
    async def stream_chat(
        self,
        system_instruction: str,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_output_tokens: int = 1500,
        tool_handler: Optional[Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream text chunks from the LLM.
        Must yield non-empty string chunks.
        """
        pass
