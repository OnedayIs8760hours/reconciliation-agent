# LLM Excel Tools

`agent/tools/excel_toolset.py` 提供给 LLM 编排层使用的 Excel 操作能力。

设计原则：

1. LLM 不直接操作 openpyxl 对象。
2. 每次操作都必须使用 `ExcelToolRequest` 描述意图。
3. 默认写操作要求提供 `output_path`，避免覆盖原始文件。
4. 工具返回 `ExcelToolObservation`，包含有限预览、变更单元格、告警和输出路径。
5. 复杂业务规则仍由 core/workflow 层执行，Excel tools 只提供可审计的底层表格能力。

## 支持操作

- `inspect_workbook`：查看工作簿结构、表头、预览、公式/显示告警。
- `read_range`：读取指定范围，受最大单元格数量限制。
- `write_cell`：写入指定单元格。
- `write_row`：按列号写入一行。
- `append_columns`：追加表头列。
- `insert_rows`：插入行。
- `copy_row_style`：复制整行样式。
- `mark_rows`：标注行并写入状态/说明列。
- `set_formula`：写入公式。
- `reset_view`：复位视图并冻结窗格。
- `save_as`：另存为。

## 示例

```python
from pathlib import Path
from agent.tools import CellWrite, ExcelOperationName, ExcelToolRequest, ExcelToolset

observation = ExcelToolset().execute(
    ExcelToolRequest(
        operation=ExcelOperationName.WRITE_CELL,
        workbook_path=Path("input.xlsx"),
        output_path=Path("outputs/output.xlsx"),
        cell_writes=[CellWrite(coordinate="Q1", value="匹配状态")],
    )
)
```
