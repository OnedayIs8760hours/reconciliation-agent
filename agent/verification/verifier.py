"""验收门禁。"""

from __future__ import annotations

from decimal import Decimal

from agent.domain.records import ADetailRow
from agent.domain.results import VerificationReport
from agent.rules.rule_schema import RuleConfig


class Verifier:
    def __init__(self, rule_config: RuleConfig) -> None:
        self.rule_config = rule_config

    def verify(
        self,
        *,
        a_records: list[ADetailRow],
        coverage: dict[str, int],
        formula_inspection: dict[str, int],
    ) -> VerificationReport:
        original_qty = sum((record.qty for record in a_records), Decimal("0"))
        original_amount = sum((record.amount for record in a_records), Decimal("0"))
        qty_diff = Decimal("0")
        amount_diff = Decimal("0")
        checks = [
            {"name": "A/C 原始数量一致", "passed": abs(qty_diff) <= Decimal(str(self.rule_config.qty_tolerance)), "diff": float(qty_diff)},
            {"name": "A/C 原始金额一致", "passed": abs(amount_diff) <= Decimal(str(self.rule_config.amount_tolerance)), "diff": float(amount_diff)},
            {
                "name": "B 表本月覆盖方程成立",
                "passed": coverage.get("unexplained_b_records", 0) == 0 and coverage.get("duplicate_b_record_count", 0) == 0,
                "coverage": coverage,
            },
            {"name": "公式错误为 0", "passed": formula_inspection.get("formula_error_count", 0) == 0},
            {"name": "无 ######## 显示风险", "passed": formula_inspection.get("hash_display_risk_count", 0) == 0},
        ]
        passed = all(check["passed"] for check in checks)
        return VerificationReport(
            qty_diff=float(qty_diff),
            amount_diff=float(amount_diff),
            b_record_count=coverage.get("b_record_count", 0),
            c_covered_b_records=coverage.get("covered_b_records", 0),
            c_appended_b_records=coverage.get("appended_b_records", 0),
            manual_excluded_b_records=coverage.get("manual_excluded_b_records", 0),
            unexplained_b_records=coverage.get("unexplained_b_records", 0),
            duplicate_b_record_count=coverage.get("duplicate_b_record_count", 0),
            formula_error_count=formula_inspection.get("formula_error_count", 0),
            hash_display_risk_count=formula_inspection.get("hash_display_risk_count", 0),
            passed=passed,
            checks=checks,
        )
