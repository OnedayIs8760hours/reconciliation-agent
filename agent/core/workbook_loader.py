"""工作簿加载。"""

from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.workbook import Workbook


def load_excel_workbook(path: Path, *, data_only: bool = False) -> Workbook:
    return load_workbook(path, data_only=data_only)
