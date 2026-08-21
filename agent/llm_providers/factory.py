"""LLM provider 工厂。"""

from __future__ import annotations

from agent.domain.config import LLMConfig
from agent.llm_providers.base import LLMProvider
from agent.llm_providers.openai_compatible_adapter import OpenAICompatibleAdapter


def build_llm_provider(config: LLMConfig | None = None) -> LLMProvider:
    config = config or LLMConfig()
    provider = config.provider.lower()
    if provider == "deepseek":
        return OpenAICompatibleAdapter(config)
    raise ValueError(f"不支持的 LLM_PROVIDER：{config.provider}")
