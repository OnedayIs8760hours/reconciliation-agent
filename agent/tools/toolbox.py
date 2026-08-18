"""封装确定性对账操作的工具外观。"""

from pathlib import Path

from agent.core.c_table_builder import CTableBuilder
from agent.core.file_detector import WorkbookDetector
from agent.core.workbook_loader import WorkbookLoader
from agent.domain.schemas import WorkbookKind
from agent.tools.excel_models import ExcelToolObservation, ExcelToolRequest
from agent.tools.excel_toolset import ExcelToolset
from agent.tools.types import ToolResult


class ReconciliationToolbox:
    """用于 LLM 编排的小型、可审计工具接口。"""

    def __init__(self) -> None:
        self.loader = WorkbookLoader()
        self.detector = WorkbookDetector()
        self.builder = CTableBuilder(self.loader)
        self.excel = ExcelToolset(self.loader)

    def identify_workbook(self, path: Path) -> ToolResult:
        identity = self.detector.identify(path)
        return ToolResult.success(
            "identify_workbook",
            f"识别为{identity.kind}，置信度{identity.confidence:.2f}",
            data=identity.model_dump(mode="json"),
        )

    def build_c_draft(self, a_table_path: Path, c_table_path: Path) -> ToolResult:
        self.detector.assert_expected(a_table_path, WorkbookKind.A_TABLE)
        output = self.builder.build_from_a_table(a_table_path, c_table_path)
        return ToolResult.success("build_c_draft", "已从A表完整复制生成C表初稿", artifacts=[output])

    def operate_excel(self, request: ExcelToolRequest) -> ExcelToolObservation:
        """为 LLM 编排层运行一个类型化 Excel 操作。"""
        return self.excel.execute(request)
