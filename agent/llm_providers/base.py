"""LLM provider 抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class LLMMessage:
    role: str
    content: str


@dataclass(slots=True)
class LLMResponse:
    content: str
    model: str
    provider: str


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> LLMResponse:
        """返回一次聊天补全文本。"""
