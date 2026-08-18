"""面向 LLM 工具的类型化 Excel 操作模型。"""

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class ExcelOperationName(StrEnum):
    """暴露给 LLM 层的允许确定性 Excel 操作。"""

    INSPECT_WORKBOOK = "inspect_workbook"
    READ_RANGE = "read_range"
    WRITE_CELL = "write_cell"
    WRITE_ROW = "write_row"
    APPEND_COLUMNS = "append_columns"
    INSERT_ROWS = "insert_rows"
    COPY_ROW_STYLE = "copy_row_style"
    MARK_ROWS = "mark_rows"
    SET_FORMULA = "set_formula"
    RESET_VIEW = "reset_view"
    SAVE_AS = "save_as"


class CellWrite(BaseModel):
    """一条单元格写入请求。"""

    coordinate: str = Field(description="Excel coordinate such as A1 or Q5.")
    value: Any = None
    number_format: str | None = None


class RowWrite(BaseModel):
    """一条使用 1 起始列号的行写入请求。"""

    row_number: int = Field(gt=0)
    values: dict[int, Any] = Field(description="Map of 1-indexed column number to value.")


class RowMark(BaseModel):
    """一条行标记请求。"""

    row_number: int = Field(gt=0)
    note: str
    fill_color: str = Field(default="FFF2CC", description="ARGB/RGB hex color accepted by openpyxl.")
    status_column_header: str = "LLM工具标注状态"
    note_column_header: str = "LLM工具标注说明"
    status: str = "需复核"


class FormulaWrite(BaseModel):
    """一条公式写入请求。"""

    coordinate: str
    formula: str = Field(description="Formula beginning with '='.")
    number_format: str | None = None


class ExcelToolRequest(BaseModel):
    """Excel 工具执行的通用请求封装。"""

    operation: ExcelOperationName
    workbook_path: Path
    sheet_name: str | None = None
    output_path: Path | None = None
    range_address: str | None = None
    cell_writes: list[CellWrite] = Field(default_factory=list)
    row_writes: list[RowWrite] = Field(default_factory=list)
    append_headers: list[str] = Field(default_factory=list)
    insert_at: int | None = None
    insert_count: int = 1
    source_row: int | None = None
    target_row: int | None = None
    row_marks: list[RowMark] = Field(default_factory=list)
    formula_writes: list[FormulaWrite] = Field(default_factory=list)
    freeze_panes: str | None = "A2"
    top_left_cell: str = "A1"
    max_preview_rows: int = 50
    dry_run: bool = False


class ExcelToolObservation(BaseModel):
    """Excel 操作后返回给 LLM 层的结构化观察结果。"""

    operation: ExcelOperationName
    ok: bool
    workbook_path: Path
    output_path: Path | None = None
    sheet_name: str | None = None
    message: str
    changed_cells: list[str] = Field(default_factory=list)
    changed_rows: list[int] = Field(default_factory=list)
    headers: list[str] = Field(default_factory=list)
    preview: list[list[Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExcelSafetyPolicy(BaseModel):
    """面向 LLM 的 Excel 操作护栏。"""

    require_output_path_for_mutation: bool = True
    allowed_extensions: tuple[str, ...] = (".xlsx", ".xlsm")
    max_cells_per_read: int = 500
    max_cells_per_write: int = 500
    allow_macro_workbooks: bool = True
    default_mutation_mode: Literal["copy", "in_place"] = "copy"
