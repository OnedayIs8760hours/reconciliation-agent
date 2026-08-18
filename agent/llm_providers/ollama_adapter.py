"""Ollama local HTTP LLM provider adapter."""

from typing import Any

from agent.llm_providers.base import LLMProviderError, LLMResponse


class OllamaAdapter:
    """通过本地 Ollama HTTP API 调用模型。"""

    provider = "ollama"

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        client: Any | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        if client is not None:
            self.client = client
            self._owns_client = False
            return

        import httpx

        self.client = httpx.Client(timeout=timeout_seconds)
        self._owns_client = True

    def complete(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        """调用 Ollama /api/chat 并规范化文本结果。"""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        try:
            response = self.client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # noqa: BLE001 - http clients expose different exception types
            raise LLMProviderError(self.provider, str(exc)) from exc

        message = data.get("message") or {}
        text = message.get("content") or data.get("response") or ""
        return LLMResponse(text=text, model=self.model, provider=self.provider)

    def close(self) -> None:
        """关闭内部 HTTP client。"""
        if self._owns_client:
            self.client.close()
