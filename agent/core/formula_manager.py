"""公式检查与基础维护。"""

from __future__ import annotations

ERROR_PREFIXES = ("#DIV/0!", "#N/A", "#NAME?", "#NULL!", "#NUM!", "#REF!", "#VALUE!")


class FormulaManager:
    def inspect(self, worksheet) -> dict[str, int]:
        formula_errors = 0
        hash_risks = 0
        for row in worksheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    if cell.value.startswith(ERROR_PREFIXES):
                        formula_errors += 1
                    if "########" in cell.value:
                        hash_risks += 1
        return {"formula_error_count": formula_errors, "hash_display_risk_count": hash_risks}
