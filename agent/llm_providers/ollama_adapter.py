from __future__ import annotations

from typing import Any

import httpx

from agent.domain import LLMProviderName

from .base import LLMProviderError, LLMResponse


class OllamaAdapter:
    provider: LLMProviderName = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 60.0,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def complete(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        try:
            response = self.client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:  # pragma: no cover - exercised through provider tests with fakes
            raise LLMProviderError(f"Ollama provider request failed: {exc}") from exc

        return LLMResponse(
            text=self._extract_text(body),
            model=self.model,
            provider=self.provider,
        )

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if close is not None:
            close()

    @staticmethod
    def _extract_text(body: dict[str, Any]) -> str:
        message = body.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
        response = body.get("response")
        return response if isinstance(response, str) else ""
