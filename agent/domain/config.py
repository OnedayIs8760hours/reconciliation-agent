from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Literal类型用于限定一个变量只能取某几个固定的字面值。
LLMProviderName = Literal["anthropic", "openai", "deepseek", "qwen", "ollama"]


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: LLMProviderName = Field(default="anthropic")
    model: str | None = Field(default=None, min_length=1)
    base_url: str | None = Field(default=None, min_length=1)
    api_key_env: str | None = Field(default=None, min_length=1)
    timeout_seconds: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
