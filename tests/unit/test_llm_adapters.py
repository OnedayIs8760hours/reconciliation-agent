"""LLM provider adapters tests."""

from types import SimpleNamespace

import pytest

from agent.domain.config import LLMConfig
from agent.llm import ClaudeReconciliationAgent, ReconciliationLLMAgent
from agent.llm_providers import (
    AnthropicAdapter,
    LLMProviderError,
    OllamaAdapter,
    OpenAIAdapter,
    OpenAICompatibleAdapter,
    resolved_base_url,
    resolved_model,
)


class FakeAnthropicMessages:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="Claude 响应")])


class FakeAnthropicClient:
    def __init__(self) -> None:
        self.messages = FakeAnthropicMessages()


class FakeOpenAICompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(content="OpenAI 响应")
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeOpenAICompletions())


class FakeHTTPResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"message": {"content": "Ollama 响应"}}


class FakeHTTPClient:
    def __init__(self) -> None:
        self.url = None
        self.payload = None

    def post(self, url: str, json: dict):
        self.url = url
        self.payload = json
        return FakeHTTPResponse()


class FailingAdapter:
    provider = "test"
    model = "fake"

    def complete(self, prompt: str, *, max_tokens: int):
        raise LLMProviderError(self.provider, "failed")


def test_anthropic_adapter_parses_text_and_uses_adaptive_thinking() -> None:
    client = FakeAnthropicClient()
    response = AnthropicAdapter(model="claude-opus-5", client=client).complete("hi", max_tokens=100)

    assert response.text == "Claude 响应"
    assert response.provider == "anthropic"
    assert client.messages.kwargs["thinking"] == {"type": "adaptive"}


def test_openai_adapter_parses_chat_completion_without_thinking() -> None:
    client = FakeOpenAIClient()
    response = OpenAIAdapter(model="gpt-4.1", client=client).complete("hi", max_tokens=100)

    assert response.text == "OpenAI 响应"
    assert response.provider == "openai"
    assert "thinking" not in client.chat.completions.kwargs


def test_deepseek_factory_uses_openai_compatible_defaults() -> None:
    config = LLMConfig(provider="deepseek")

    assert resolved_model(config) == "deepseek-chat"
    assert resolved_base_url(config) == "https://api.deepseek.com"
    assert isinstance(
        OpenAICompatibleAdapter(
            provider=config.provider,
            model=resolved_model(config),
            base_url=resolved_base_url(config),
            client=FakeOpenAIClient(),
        ),
        OpenAICompatibleAdapter,
    )


def test_qwen_factory_uses_openai_compatible_defaults() -> None:
    config = LLMConfig(provider="qwen")

    assert resolved_model(config) == "qwen-plus"
    assert resolved_base_url(config) == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert isinstance(
        OpenAICompatibleAdapter(
            provider=config.provider,
            model=resolved_model(config),
            base_url=resolved_base_url(config),
            client=FakeOpenAIClient(),
        ),
        OpenAICompatibleAdapter,
    )


def test_ollama_adapter_parses_local_http_response() -> None:
    client = FakeHTTPClient()
    response = OllamaAdapter(model="qwen2.5", base_url="http://localhost:11434", client=client).complete(
        "hi",
        max_tokens=100,
    )

    assert response.text == "Ollama 响应"
    assert response.provider == "ollama"
    assert client.url == "http://localhost:11434/api/chat"
    assert client.payload["options"]["num_predict"] == 100


def test_reconciliation_agent_keeps_workflow_facing_api() -> None:
    agent = ReconciliationLLMAgent(adapter=FailingAdapter())

    with pytest.raises(LLMProviderError):
        agent.explain_plan(rule_summary="规则", available_tools=["inspect_workbook"])


def test_claude_reconciliation_agent_accepts_legacy_fake_client() -> None:
    client = FakeAnthropicClient()
    agent = ClaudeReconciliationAgent(client=client)

    response = agent.suggest_repairs("失败报告")

    assert response.text == "Claude 响应"
    assert response.model == "claude-opus-5"
