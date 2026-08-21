"""运行结果模型。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class VerificationReport(BaseModel):
    qty_diff: float = 0
    amount_diff: float = 0
    b_record_count: int = 0
    c_covered_b_records: int = 0
    c_appended_b_records: int = 0
    manual_excluded_b_records: int = 0
    unexplained_b_records: int = 0
    duplicate_b_record_count: int = 0
    formula_error_count: int = 0
    hash_display_risk_count: int = 0
    passed: bool = False
    checks: list[dict[str, Any]] = Field(default_factory=list)


class RunReport(BaseModel):
    status: Literal["passed", "failed"]
    run_id: str
    c_file: Path | None = None
    report_file: Path
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str | None = None
    verification: VerificationReport
    progress: int = 100
    matching: dict[str, Any] = Field(default_factory=dict)
    coverage: dict[str, int] = Field(default_factory=dict)
    exceptions: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.status == "passed"
