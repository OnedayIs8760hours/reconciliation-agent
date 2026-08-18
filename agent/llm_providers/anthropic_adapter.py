"""Claude/Anthropic LLM provider adapter."""

from typing import Any

from agent.llm_providers.base import LLMProviderError, LLMResponse


class AnthropicAdapter:
    """使用官方 Anthropic SDK 调用 Claude。"""

    provider = "anthropic"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        client: Any | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self.model = model
        if client is not None:
            self.client = client
            return

        from anthropic import Anthropic

        kwargs: dict[str, Any] = {
            "timeout": timeout_seconds,
            "max_retries": max_retries,
        }
        if api_key:
            kwargs["api_key"] = api_key
        self.client = Anthropic(**kwargs)

    def complete(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        """调用 Claude Messages API 并规范化文本结果。"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # noqa: BLE001 - provider SDK errors vary by version
            raise LLMProviderError(self.provider, str(exc)) from exc

        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        return LLMResponse(text=text, model=self.model, provider=self.provider)
