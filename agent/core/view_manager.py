"""视图调整。"""

from __future__ import annotations


class ViewManager:
    def reset(self, worksheet, header_row: int) -> None:
        worksheet.freeze_panes = f"A{header_row + 1}"
        worksheet.sheet_view.topLeftCell = "A1"
        worksheet.sheet_view.selection[0].sqref = "A1"
        worksheet.sheet_view.selection[0].activeCell = "A1"
        for column_cells in worksheet.columns:
            max_len = 8
            column_letter = column_cells[0].column_letter
            for cell in column_cells[:100]:
                if cell.value is not None:
                    max_len = max(max_len, min(30, len(str(cell.value)) + 2))
            worksheet.column_dimensions[column_letter].width = max_len
