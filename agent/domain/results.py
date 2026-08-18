"""工作流和验证输出的结构化结果模型。"""

from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field


class VerificationCheck(BaseModel):
    """一条验收检查结果。"""

    name: str
    passed: bool
    summary: str
    details: dict[str, object] = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    """C 表工作流返回的最终结果。"""

    accepted: bool
    c_table_path: Path | None = None
    marked_b_table_path: Path | None = None
    report_path: Path | None = None
    checks: list[VerificationCheck] = Field(default_factory=list)
    a_quantity_total: Decimal | None = None
    c_quantity_total: Decimal | None = None
    a_amount_total: Decimal | None = None
    c_amount_total: Decimal | None = None
    b_month_records: int = 0
    c_accepted_records: int = 0
    b_marked_missing_records: int = 0
    manually_excluded_records: int = 0
    uncovered_records: int = 0

    def to_display(self) -> str:
        status = "✅ 可交付" if self.accepted else "❌ 未通过验收"
        lines = [f"{status}"]
        if self.c_table_path:
            lines.append(f"C 表: {self.c_table_path}")
        if self.marked_b_table_path:
            lines.append(f"已标注 B 表: {self.marked_b_table_path}")
        if self.report_path:
            lines.append(f"核查报告: {self.report_path}")
        for check in self.checks:
            icon = "✅" if check.passed else "❌"
            lines.append(f"{icon} {check.name}: {check.summary}")
        return "\n".join(lines)
