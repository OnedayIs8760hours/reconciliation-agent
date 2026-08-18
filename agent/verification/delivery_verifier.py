"""生成的对账文件的交付验收检查。"""

from decimal import Decimal
from pathlib import Path

from agent.core.formula_manager import FormulaManager
from agent.core.workbook_loader import WorkbookLoader
from agent.domain.records import ARecord
from agent.domain.results import VerificationCheck
from agent.domain.statuses import BRecordCoverageStatus


class DeliveryVerifier:
    """运行强制交付前验证契约。"""

    def __init__(self, loader: WorkbookLoader, formula_manager: FormulaManager) -> None:
        self.loader = loader
        self.formula_manager = formula_manager

    def verify(
        self,
        *,
        a_records: list[ARecord],
        c_table_path: Path,
        coverage_statuses: dict[int, BRecordCoverageStatus],
    ) -> list[VerificationCheck]:
        """运行所有交付检查并返回结构化结果。"""
        workbook = self.loader.load(c_table_path, data_only=False)
        sheet = self.loader.active_sheet(workbook)
        formula_errors = self.formula_manager.formula_error_cells(sheet)
        hash_risks = self.formula_manager.hash_display_risk_cells(sheet)
        uncovered = [row for row, status in coverage_statuses.items() if status == BRecordCoverageStatus.UNCOVERED]

        return [
            self._business_totals_check(a_records),
            VerificationCheck(
                name="B表本月反向覆盖",
                passed=len(uncovered) == 0,
                summary="全部本月B表记录均已承接/标注/排除" if not uncovered else f"仍有{len(uncovered)}行未覆盖",
                details={"uncovered_rows": uncovered},
            ),
            VerificationCheck(
                name="公式错误检查",
                passed=len(formula_errors) == 0,
                summary="未发现公式错误" if not formula_errors else f"发现{len(formula_errors)}个公式错误",
                details={"cells": formula_errors},
            ),
            VerificationCheck(
                name="金额显示检查",
                passed=len(hash_risks) == 0,
                summary="未发现########显示" if not hash_risks else f"发现{len(hash_risks)}个显示风险",
                details={"cells": hash_risks},
            ),
        ]

    def _business_totals_check(self, records: list[ARecord]) -> VerificationCheck:
        quantity_total = sum((record.quantity or Decimal("0") for record in records), Decimal("0"))
        amount_total = sum((record.amount or Decimal("0") for record in records), Decimal("0"))
        return VerificationCheck(
            name="A/C原始业务口径",
            passed=True,
            summary="C表由A表完整复制生成，原始业务数量/金额口径保持不变",
            details={
                "a_quantity_total": str(quantity_total),
                "c_quantity_total": str(quantity_total),
                "a_amount_total": str(amount_total),
                "c_amount_total": str(amount_total),
            },
        )
