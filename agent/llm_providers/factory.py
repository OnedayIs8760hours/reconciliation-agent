from __future__ import annotations

from dataclasses import dataclass

from agent.domain import LLMConfig, LLMProviderName

from .anthropic_adapter import AnthropicAdapter
from .base import LLMProviderAdapter
from .ollama_adapter import OllamaAdapter
from .openai_adapter import OpenAIAdapter
from .openai_compatible_adapter import OpenAICompatibleAdapter


@dataclass(frozen=True)
class ProviderDefaults:
    model: str
    api_key_env: str | None = None
    base_url: str | None = None


PROVIDER_DEFAULTS: dict[LLMProviderName, ProviderDefaults] = {
    "anthropic": ProviderDefaults(model="claude-opus-5", api_key_env="ANTHROPIC_API_KEY"),
    "openai": ProviderDefaults(model="gpt-4.1", api_key_env="OPENAI_API_KEY"),
    "deepseek": ProviderDefaults(
        model="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com",
    ),
    "qwen": ProviderDefaults(
        model="qwen-plus",
        api_key_env="DASHSCOPE_API_KEY",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "ollama": ProviderDefaults(model="qwen3.5:9b", base_url="http://localhost:11434"),
}


def resolve_llm_config(config: LLMConfig) -> LLMConfig:
    defaults = PROVIDER_DEFAULTS[config.provider]
    # 拿原来的 config 复制一份，然后把 model、base_url、api_key_env 这几个字段补成最终值
    return config.model_copy(
        update={
            "model": config.model or defaults.model,
            "base_url": config.base_url or defaults.base_url,
            "api_key_env": config.api_key_env or defaults.api_key_env,
        }
    )


def build_llm_adapter(config: LLMConfig) -> LLMProviderAdapter:
    resolved = resolve_llm_config(config)
    if resolved.model is None:
        raise ValueError(f"No default model configured for provider {resolved.provider}")

    if resolved.provider == "anthropic":
        return AnthropicAdapter(
            model=resolved.model,
            api_key_env=resolved.api_key_env or "ANTHROPIC_API_KEY",
            timeout_seconds=resolved.timeout_seconds,
            max_retries=resolved.max_retries,
        )

    if resolved.provider == "openai":
        return OpenAIAdapter(
            model=resolved.model,
            api_key_env=resolved.api_key_env or "OPENAI_API_KEY",
            base_url=resolved.base_url,
            timeout_seconds=resolved.timeout_seconds,
            max_retries=resolved.max_retries,
        )

    if resolved.provider in {"deepseek", "qwen"}:
        if resolved.base_url is None or resolved.api_key_env is None:
            raise ValueError(f"Provider {resolved.provider} requires base_url and api_key_env")
        return OpenAICompatibleAdapter(
            provider=resolved.provider,
            model=resolved.model,
            api_key_env=resolved.api_key_env,
            base_url=resolved.base_url,
            timeout_seconds=resolved.timeout_seconds,
            max_retries=resolved.max_retries,
        )

    if resolved.provider == "ollama":
        return OllamaAdapter(
            model=resolved.model,
            base_url=resolved.base_url or "http://localhost:11434",
            timeout_seconds=resolved.timeout_seconds,
        )

    raise ValueError(f"Unsupported LLM provider: {resolved.provider}")
