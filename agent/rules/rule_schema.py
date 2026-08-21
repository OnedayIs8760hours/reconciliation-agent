"""规则配置结构。"""

from pydantic import BaseModel, Field


class RuleConfig(BaseModel):
    rule_pack: str = "c_table_default"
    rule_version: str = "2026.08.mvp"
    missing_b_policy: str = "append_to_c_tail"
    amount_tolerance: float = 0.01
    qty_tolerance: float = 0.0001
    date_tolerance_days: int = 3
    force_a_c_total_check: bool = True
    force_b_coverage_check: bool = True
    force_formula_error_check: bool = True
    reverse_check_current_month_b: bool = True
    header_aliases: dict[str, list[str]] = Field(default_factory=dict)
