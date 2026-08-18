"""OpenAI-compatible provider adapters."""

from typing import Any

from agent.llm_providers.openai_adapter import OpenAIAdapter


class OpenAICompatibleAdapter(OpenAIAdapter):
    """复用 OpenAI SDK 接入 DeepSeek、Qwen 等兼容接口。"""

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        client: Any | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        super().__init__(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            client=client,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
