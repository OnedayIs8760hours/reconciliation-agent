"""工作簿加载与保存辅助工具。"""

from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet


class WorkbookLoader:
    """供确定性工具使用的集中式 openpyxl 适配器。"""

    def load(self, path: Path, *, data_only: bool = False) -> Workbook:
        """从磁盘加载 Excel 工作簿。"""
        if not path.exists():
            raise FileNotFoundError(path)
        return load_workbook(path, data_only=data_only)

    def active_sheet(self, workbook: Workbook) -> Worksheet:
        """返回对账工作流使用的活动工作表。"""
        return workbook.active

    def save(self, workbook: Workbook, path: Path) -> Path:
        """持久化工作簿，并在必要时创建输出目录。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(path)
        return path

    def iter_data_rows(self, sheet: Worksheet, *, header_row: int = 1) -> list[tuple[int, tuple[Any, ...]]]:
        """返回表头下方的非空行及其工作表行号。"""
        rows: list[tuple[int, tuple[Any, ...]]] = []
        for row in sheet.iter_rows(min_row=header_row + 1, values_only=False):
            values = tuple(cell.value for cell in row)
            if any(value not in (None, "") for value in values):
                rows.append((row[0].row, values))
        return rows
