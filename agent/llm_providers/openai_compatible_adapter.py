from __future__ import annotations

from agent.domain import LLMProviderName

from .openai_adapter import OpenAIAdapter


class OpenAICompatibleAdapter(OpenAIAdapter):
    def __init__(
        self,
        provider: LLMProviderName,
        model: str,
        api_key_env: str,
        base_url: str,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        client: object | None = None,
    ) -> None:
        super().__init__(
            model=model,
            api_key_env=api_key_env,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            client=client,
            provider=provider,
        )
