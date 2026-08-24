from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from agent.domain import LLMProviderName

from .base import LLMProviderError, LLMResponse


class OpenAIAdapter:
    provider: LLMProviderName = "openai"

    def __init__(
        self,
        model: str,
        api_key_env: str = "OPENAI_API_KEY",
        base_url: str | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        client: Any | None = None,
        provider: LLMProviderName = "openai",
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = OpenAI(
                api_key=os.getenv(self.api_key_env),
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                max_retries=self.max_retries,
            )
        return self._client

    def complete(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
        except Exception as exc:  # pragma: no cover - exercised through provider tests with fakes
            raise LLMProviderError(f"{self.provider} provider request failed: {exc}") from exc

        message = response.choices[0].message
        return LLMResponse(
            text=message.content or "",
            model=self.model,
            provider=self.provider,
        )
