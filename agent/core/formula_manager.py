"""工作簿公式与显示安全检查。"""

from openpyxl.worksheet.worksheet import Worksheet


class FormulaManager:
    """交付前检查公式单元格和金额显示风险区域。"""

    ERROR_PREFIXES = ("#DIV/0!", "#N/A", "#NAME?", "#NULL!", "#NUM!", "#REF!", "#VALUE!")

    def formula_error_cells(self, sheet: Worksheet) -> list[str]:
        """返回缓存值或字面值显示公式错误的单元格坐标。"""
        errors: list[str] = []
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith(self.ERROR_PREFIXES):
                    errors.append(cell.coordinate)
        return errors

    def hash_display_risk_cells(self, sheet: Worksheet) -> list[str]:
        """返回文本已显示 Excel 井号溢出的单元格。"""
        risks: list[str] = []
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and "########" in cell.value:
                    risks.append(cell.coordinate)
        return risks

    def widen_amount_columns(self, sheet: Worksheet, min_width: float = 14.0) -> None:
        """为可能的金额列设置安全的最小宽度。"""
        for column_cells in sheet.columns:
            header = str(column_cells[0].value or "")
            if "金额" in header or "单价" in header:
                letter = column_cells[0].column_letter
                sheet.column_dimensions[letter].width = max(
                    sheet.column_dimensions[letter].width or 0,
                    min_width,
                )
