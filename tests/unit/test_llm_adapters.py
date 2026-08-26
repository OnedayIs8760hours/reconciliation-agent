from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from agent import ClaudeReconciliationAgent, LLMConfig, ReconciliationLLMAgent
from agent.llm_providers import (
    AnthropicAdapter,
    LLMResponse,
    OllamaAdapter,
    OpenAIAdapter,
    OpenAICompatibleAdapter,
    build_llm_adapter,
    resolve_llm_config,
)


class FakeAnthropicMessages:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="Claude 响应")])


class FakeAnthropicClient:
    def __init__(self) -> None:
        self.messages = FakeAnthropicMessages()


class FakeOpenAICompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        message = SimpleNamespace(content="OpenAI 响应")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeOpenAICompletions())


class FakeHTTPResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"message": {"content": "Ollama 响应"}}


class FakeHTTPClient:
    def __init__(self) -> None:
        self.url = None
        self.payload = None
        self.closed = False

    def post(self, url: str, json: dict[str, object]) -> FakeHTTPResponse:
        self.url = url
        self.payload = json
        return FakeHTTPResponse()

    def close(self) -> None:
        self.closed = True


class FakeAdapter:
    provider = "openai"
    model = "fake-model"

    def __init__(self) -> None:
        self.prompt = None
        self.max_tokens = None

    def complete(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        self.prompt = prompt
        self.max_tokens = max_tokens
        return LLMResponse(text="fake 响应", model=self.model, provider=self.provider)


def test_resolve_llm_config_applies_provider_defaults() -> None:
    assert resolve_llm_config(LLMConfig()).model == "claude-opus-5"
    deepseek = resolve_llm_config(LLMConfig(provider="deepseek"))
    assert deepseek.model == "deepseek-chat"
    assert deepseek.api_key_env == "DEEPSEEK_API_KEY"
    assert deepseek.base_url == "https://api.deepseek.com"


def test_invalid_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        LLMConfig(provider="bad-provider")  # type: ignore[arg-type]


def test_factory_selects_expected_adapter_types() -> None:
    assert isinstance(build_llm_adapter(LLMConfig(provider="anthropic")), AnthropicAdapter)
    assert isinstance(build_llm_adapter(LLMConfig(provider="openai")), OpenAIAdapter)
    assert isinstance(build_llm_adapter(LLMConfig(provider="deepseek")), OpenAICompatibleAdapter)
    assert isinstance(build_llm_adapter(LLMConfig(provider="qwen")), OpenAICompatibleAdapter)
    assert isinstance(build_llm_adapter(LLMConfig(provider="ollama")), OllamaAdapter)


def test_anthropic_adapter_parses_text_and_keeps_thinking_local() -> None:
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


def test_openai_compatible_adapter_preserves_provider_name() -> None:
    client = FakeOpenAIClient()
    response = OpenAICompatibleAdapter(
        provider="qwen",
        model="qwen-plus",
        api_key_env="DASHSCOPE_API_KEY",
        base_url="https://example.test/v1",
        client=client,
    ).complete("hi")

    assert response.text == "OpenAI 响应"
    assert response.provider == "qwen"


def test_deepseek_adapter_disables_thinking_for_json_prompts() -> None:
    client = FakeOpenAIClient()
    response = OpenAICompatibleAdapter(
        provider="deepseek",
        model="deepseek-v4-flash",
        api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com",
        client=client,
    ).complete("请只输出 JSON：{}", max_tokens=128)

    kwargs = client.chat.completions.kwargs
    assert response.text == "OpenAI 响应"
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["extra_body"] == {
        "reasoning_effort": "none",
        "thinking": {"type": "disabled"},
    }


def test_ollama_adapter_posts_to_chat_endpoint_and_maps_max_tokens() -> None:
    client = FakeHTTPClient()
    response = OllamaAdapter(model="qwen2.5", base_url="http://localhost:11434/", client=client).complete(
        "hi",
        max_tokens=64,
    )

    assert response.text == "Ollama 响应"
    assert client.url == "http://localhost:11434/api/chat"
    assert client.payload["options"] == {"num_predict": 64}


def test_agent_accepts_injected_adapter_and_exposes_model() -> None:
    adapter = FakeAdapter()
    llm_agent = ReconciliationLLMAgent(provider="openai", adapter=adapter)
    response = llm_agent.complete("hello", max_tokens=12)

    assert llm_agent.model == "fake-model"
    assert response.text == "fake 响应"
    assert adapter.prompt == "hello"
    assert adapter.max_tokens == 12


def test_product_mapping_uses_large_default_output_budget() -> None:
    adapter = FakeAdapter()
    llm_agent = ReconciliationLLMAgent(provider="openai", adapter=adapter)

    llm_agent.analyze_product_mapping(["商品A"], ["商品A"])

    assert adapter.max_tokens == 40960


def test_claude_compat_agent_defaults_to_anthropic_with_injected_adapter() -> None:
    adapter = FakeAdapter()
    llm_agent = ClaudeReconciliationAgent(adapter=adapter)

    assert llm_agent.provider == "anthropic"
