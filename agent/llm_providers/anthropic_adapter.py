from __future__ import annotations

import os
from typing import Any

from anthropic import Anthropic

from agent.domain import LLMProviderName

from .base import LLMProviderError, LLMResponse


class AnthropicAdapter:
    provider: LLMProviderName = "anthropic"

    def __init__(
        self,
        model: str,
        api_key_env: str = "ANTHROPIC_API_KEY",
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = Anthropic(
                api_key=os.getenv(self.api_key_env),
                timeout=self.timeout_seconds,
                max_retries=self.max_retries,
            )
        return self._client

    def complete(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                thinking={"type": "adaptive"},
            )
        except Exception as exc:  # pragma: no cover - exercised through provider tests with fakes
            raise LLMProviderError(f"Anthropic provider request failed: {exc}") from exc

        return LLMResponse(
            text=self._extract_text(response),
            model=self.model,
            provider=self.provider,
        )

    @staticmethod
    def _extract_text(response: Any) -> str:
        parts: list[str] = []
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", ""))
        return "".join(parts)
