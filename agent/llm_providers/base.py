"""LLM provider adapter base types."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResponse:
    """来自 LLM 层的最小规范化响应。"""

    text: str
    model: str
    provider: str = "anthropic"


class LLMProviderError(RuntimeError):
    """统一包装底层模型供应商错误。"""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"{provider} LLM provider error: {message}")


class LLMProviderAdapter(Protocol):
    """所有模型供应商适配器需要实现的最小接口。"""

    provider: str
    model: str

    def complete(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        """针对单轮 prompt 返回纯文本响应。"""
