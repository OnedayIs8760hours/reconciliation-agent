"""运行配置模型。"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "deepseek"))
    model: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    base_url: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    api_key_env: str = "DEEPSEEK_API_KEY"
    timeout_seconds: int = 30
    max_retries: int = 1

    @property
    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env)


class ReconciliationRunRequest(BaseModel):
    a_file: Path
    b_file: Path
    month: str
    output_dir: Path
    run_id: str | None = None
    user_overrides: dict[str, Any] = Field(default_factory=dict)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}", value):
            raise ValueError("month must use YYYY-MM")
        return value


class RunContext(BaseModel):
    run_id: str
    a_path: Path
    b_path: Path
    output_dir: Path
    c_path: Path
    report_path: Path
    month: str
    user_overrides: dict[str, Any] = Field(default_factory=dict)


RunStatus = Literal["passed", "failed"]
