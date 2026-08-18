"""LLM provider adapter factory."""

from __future__ import annotations

import os
from dataclasses import dataclass

from agent.domain.config import LLMConfig, LLMProviderName
from agent.llm_providers.anthropic_adapter import AnthropicAdapter
from agent.llm_providers.base import LLMProviderAdapter
from agent.llm_providers.ollama_adapter import OllamaAdapter
from agent.llm_providers.openai_adapter import OpenAIAdapter
from agent.llm_providers.openai_compatible_adapter import OpenAICompatibleAdapter


@dataclass(frozen=True)
class ProviderDefaults:
    """一个模型供应商的默认连接配置。"""

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
    "ollama": ProviderDefaults(model="qwen2.5", base_url="http://localhost:11434"),
}


def resolved_model(config: LLMConfig) -> str:
    """返回用户指定模型或 provider 默认模型。"""
    return config.model or PROVIDER_DEFAULTS[config.provider].model


def resolved_base_url(config: LLMConfig) -> str | None:
    """返回用户指定 base URL 或 provider 默认 base URL。"""
    return config.base_url or PROVIDER_DEFAULTS[config.provider].base_url


def resolved_api_key_env(config: LLMConfig) -> str | None:
    """返回用户指定 API key 环境变量名或 provider 默认环境变量名。"""
    return config.api_key_env or PROVIDER_DEFAULTS[config.provider].api_key_env


def resolved_api_key(config: LLMConfig) -> str | None:
    """从环境变量中读取 API key，不在代码中硬编码密钥。"""
    env_name = resolved_api_key_env(config)
    if env_name is None:
        return None
    return os.getenv(env_name)


def build_llm_adapter(config: LLMConfig) -> LLMProviderAdapter:
    """根据配置构建对应模型供应商适配器。"""
    model = resolved_model(config)
    base_url = resolved_base_url(config)
    api_key = resolved_api_key(config)

    if config.provider == "anthropic":
        return AnthropicAdapter(
            model=model,
            api_key=api_key,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
    if config.provider == "openai":
        return OpenAIAdapter(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
    if config.provider in {"deepseek", "qwen"}:
        return OpenAICompatibleAdapter(
            provider=config.provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
    if config.provider == "ollama":
        return OllamaAdapter(
            model=model,
            base_url=base_url or "http://localhost:11434",
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )

    raise ValueError(f"Unsupported LLM provider: {config.provider}")
