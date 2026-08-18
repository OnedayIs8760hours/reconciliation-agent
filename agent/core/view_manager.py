"""交付前的工作表视图规范化。"""

from openpyxl.worksheet.worksheet import Worksheet


class ViewManager:
    """将交付视图要求应用到生成的工作簿。"""

    def reset(self, sheet: Worksheet, *, freeze_below_header: bool = True) -> None:
        """将活动视图重置到 A1，并冻结表头下方窗格。"""
        sheet.sheet_view.topLeftCell = "A1"
        sheet.sheet_view.selection[0].sqref = "A1"
        sheet.sheet_view.selection[0].activeCell = "A1"
        if freeze_below_header:
            sheet.freeze_panes = "A2"
