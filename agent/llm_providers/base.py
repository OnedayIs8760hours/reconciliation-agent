from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent.domain import LLMProviderName


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    provider: LLMProviderName


class LLMProviderError(RuntimeError):
    """Raised when a model provider request fails."""

# 结构化类型接口
class LLMProviderAdapter(Protocol):
    provider: LLMProviderName
    model: str

    def complete(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        """Return a provider-neutral text completion."""
