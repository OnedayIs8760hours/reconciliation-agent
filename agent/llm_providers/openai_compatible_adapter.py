"""OpenAI-compatible LLM provider。"""

from __future__ import annotations

from openai import OpenAI

from agent.domain.config import LLMConfig
from agent.llm_providers.base import LLMMessage, LLMProvider, LLMResponse


class OpenAICompatibleAdapter(LLMProvider):
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        api_key = config.api_key
        if not api_key:
            raise ValueError(f"缺少环境变量 {config.api_key_env}")
        self.client = OpenAI(
            api_key=api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
        )

    def complete(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": message.role, "content": message.content} for message in messages],
            temperature=temperature,
        )
        content = response.choices[0].message.content or ""
        return LLMResponse(content=content, model=self.config.model, provider=self.config.provider)
