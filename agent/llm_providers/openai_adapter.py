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
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }

        if "只输出 JSON" in prompt:
            request_kwargs["response_format"] = {"type": "json_object"}

        if self.provider == "deepseek":
            request_kwargs["extra_body"] = {
                "reasoning_effort": "none",
                "thinking": {"type": "disabled"},
            }

        last_empty_response: object | None = None
        for _ in range(2):
            try:
                response = self.client.chat.completions.create(**request_kwargs)
            except Exception as exc:  # pragma: no cover - exercised through provider tests with fakes
                raise LLMProviderError(f"{self.provider} provider request failed: {exc}") from exc

            message = response.choices[0].message
            text = self._extract_message_text(message)
            if text:
                return LLMResponse(
                    text=text,
                    model=self.model,
                    provider=self.provider,
                )
            last_empty_response = response

        fallback_text = self._extract_empty_response_diagnostic(last_empty_response)
        return LLMResponse(
            text=fallback_text,
            model=self.model,
            provider=self.provider,
        )

    def _extract_message_text(self, message: Any) -> str:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            text = content.strip()
            if text:
                return text
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    value = item.get("text") or item.get("content")
                else:
                    value = getattr(item, "text", None) or getattr(item, "content", None)
                if isinstance(value, str) and value.strip():
                    parts.append(value.strip())
            if parts:
                return "\n".join(parts)

        reasoning_content = getattr(message, "reasoning_content", "")
        if isinstance(reasoning_content, str) and reasoning_content.strip():
            return reasoning_content.strip()
        return ""

    def _extract_empty_response_diagnostic(self, response: object | None) -> str:
        if response is None:
            return ""
        model_dump = getattr(response, "model_dump_json", None)
        if callable(model_dump):
            try:
                return model_dump(indent=2)
            except TypeError:
                return model_dump()
        return ""
