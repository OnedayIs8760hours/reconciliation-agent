"""OpenAI LLM provider adapter."""

from typing import Any

from agent.llm_providers.base import LLMProviderError, LLMResponse


class OpenAIAdapter:
    """使用官方 OpenAI SDK 调用 OpenAI Chat Completions。"""

    provider = "openai"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        client: Any | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        provider: str | None = None,
    ) -> None:
        self.model = model
        if provider is not None:
            self.provider = provider
        if client is not None:
            self.client = client
            return

        from openai import OpenAI

        kwargs: dict[str, Any] = {
            "timeout": timeout_seconds,
            "max_retries": max_retries,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)

    def complete(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        """调用 OpenAI-compatible Chat Completions 并规范化文本结果。"""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # noqa: BLE001 - provider SDK errors vary by version
            raise LLMProviderError(self.provider, str(exc)) from exc

        text = completion.choices[0].message.content or ""
        return LLMResponse(text=text, model=self.model, provider=self.provider)
