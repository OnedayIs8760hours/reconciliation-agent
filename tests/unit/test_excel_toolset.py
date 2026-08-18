"""面向 LLM 的 Excel 工具集测试。"""

from pathlib import Path

from openpyxl import Workbook

from agent.tools import CellWrite, ExcelOperationName, ExcelToolRequest, ExcelToolset, RowMark


def _make_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(["日期", "品名", "数量"])
    sheet.append(["2026/7/1", "测试", 1])
    workbook.save(path)


def test_excel_toolset_inspects_workbook(tmp_path: Path) -> None:
    workbook_path = tmp_path / "sample.xlsx"
    _make_workbook(workbook_path)

    observation = ExcelToolset().execute(
        ExcelToolRequest(
            operation=ExcelOperationName.INSPECT_WORKBOOK,
            workbook_path=workbook_path,
        )
    )

    assert observation.ok
    assert observation.headers == ["日期", "品名", "数量"]
    assert observation.preview[0] == ["日期", "品名", "数量"]


def test_excel_toolset_writes_to_explicit_output_path(tmp_path: Path) -> None:
    workbook_path = tmp_path / "sample.xlsx"
    output_path = tmp_path / "out.xlsx"
    _make_workbook(workbook_path)

    observation = ExcelToolset().execute(
        ExcelToolRequest(
            operation=ExcelOperationName.WRITE_CELL,
            workbook_path=workbook_path,
            output_path=output_path,
            cell_writes=[CellWrite(coordinate="D1", value="匹配状态")],
        )
    )

    assert observation.output_path == output_path
    assert "D1" in observation.changed_cells
    assert output_path.exists()


def test_excel_toolset_marks_rows(tmp_path: Path) -> None:
    workbook_path = tmp_path / "sample.xlsx"
    output_path = tmp_path / "marked.xlsx"
    _make_workbook(workbook_path)

    observation = ExcelToolset().execute(
        ExcelToolRequest(
            operation=ExcelOperationName.MARK_ROWS,
            workbook_path=workbook_path,
            output_path=output_path,
            row_marks=[RowMark(row_number=2, note="B表未承接")],
        )
    )

    assert 2 in observation.changed_rows
    assert output_path.exists()
