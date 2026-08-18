"""对账运行的运行时配置模型。"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

LLMProviderName = Literal["anthropic", "openai", "deepseek", "qwen", "ollama"]


class LLMConfig(BaseModel):
    """LLM 模型供应商和连接配置。"""

    provider: LLMProviderName = "anthropic"
    model: str | None = None
    base_url: str | None = None
    api_key_env: str | None = None
    timeout_seconds: float = 60.0
    max_retries: int = 2


class ReconciliationRunConfig(BaseModel):
    """一次 C 表运行的用户提供配置和派生配置。"""

    a_table_path: Path
    b_table_path: Path
    reconciliation_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    output_dir: Path = Path("outputs")
    company_profile: str = "default"
    c_table_filename: str | None = None
    marked_b_table_filename: str | None = None
    report_filename: str | None = None
    allow_cross_month_trace: bool = False
    on_verification_failure: Literal["stop", "repair"] = "repair"
    llm: LLMConfig = Field(default_factory=LLMConfig)

    @property
    def c_table_path(self) -> Path:
        filename = self.c_table_filename or f"C表_{self.reconciliation_month}_{self.company_profile}.xlsx"
        return self.output_dir / filename

    @property
    def marked_b_table_path(self) -> Path:
        filename = self.marked_b_table_filename or f"B表_缺失标注_{self.reconciliation_month}_{self.company_profile}.xlsx"
        return self.output_dir / filename

    @property
    def report_path(self) -> Path:
        filename = self.report_filename or f"核查报告_{self.reconciliation_month}_{self.company_profile}.md"
        return self.output_dir / filename
