"""C 表写入。"""

from __future__ import annotations

from datetime import datetime

from agent.domain.records import BRecord, MatchResult
from agent.domain.statuses import MatchStatus


TRACE_HEADERS = [
    "匹配状态",
    "匹配依据",
    "B记录ID",
    "B方向",
    "B系统时间",
    "B单号",
    "B货品编号",
    "B货品名称",
    "B规格",
    "B数量",
    "B单价",
    "B金额",
]


class CTableWriter:
    def prepare_headers(self, worksheet, header_row: int) -> dict[str, int]:
        start_col = worksheet.max_column + 1
        mapping: dict[str, int] = {}
        for offset, header in enumerate(TRACE_HEADERS):
            column = start_col + offset
            worksheet.cell(row=header_row, column=column).value = header
            mapping[header] = column
        return mapping

    def write_matches(self, worksheet, header_row: int, matches: list[MatchResult]) -> dict[str, int]:
        columns = self.prepare_headers(worksheet, header_row)
        for result in matches:
            record = result.trace_records[0] if result.trace_records else None
            worksheet.cell(row=result.a_row, column=columns["匹配状态"]).value = result.status
            worksheet.cell(row=result.a_row, column=columns["匹配依据"]).value = result.basis
            if record:
                self._write_b_record(worksheet, result.a_row, columns, record)
        return columns

    def append_unmatched_b(self, worksheet, columns: dict[str, int], unmatched_b: list[BRecord]) -> int:
        if not unmatched_b:
            return 0
        start_row = worksheet.max_row + 2
        worksheet.cell(row=start_row, column=1).value = "B表未匹配追加区"
        row = start_row + 1
        for record in unmatched_b:
            worksheet.cell(row=row, column=columns["匹配状态"]).value = MatchStatus.B_APPENDED.value
            worksheet.cell(row=row, column=columns["匹配依据"]).value = "本月 B 表记录未被 A/C 承接，按强制规则追加"
            self._write_b_record(worksheet, row, columns, record)
            row += 1
        return len(unmatched_b)

    @staticmethod
    def _fmt_time(value) -> str | None:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value) if value is not None else None

    def _write_b_record(self, worksheet, row: int, columns: dict[str, int], record: BRecord) -> None:
        values = {
            "B记录ID": record.record_id,
            "B方向": record.direction.value,
            "B系统时间": self._fmt_time(record.system_time),
            "B单号": record.document_no,
            "B货品编号": record.item_code,
            "B货品名称": record.item_name,
            "B规格": record.spec_raw,
            "B数量": float(record.qty),
            "B单价": float(record.price or 0),
            "B金额": float(record.amount),
        }
        for header, value in values.items():
            worksheet.cell(row=row, column=columns[header]).value = value
