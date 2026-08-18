"""将匹配结果写回生成的 C 表。"""

from pathlib import Path
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from agent.core.workbook_loader import WorkbookLoader
from agent.domain.records import BRecord, MatchCandidate
from agent.domain.schemas import CAppendColumns
from agent.domain.statuses import MatchDirection


class CTableMatchWriter:
    """将确定性匹配结果应用到 C 工作簿。

    多行匹配表示为独立的 C 表行。第一条 B 表行写入
    原始 A 表派生行；额外的 B 表行插入在其下方，
    原始 A 表业务列留空，仅填充追踪列。
    """

    def __init__(self, loader: WorkbookLoader, append_columns: CAppendColumns | None = None) -> None:
        self.loader = loader
        self.append_columns = append_columns or CAppendColumns()

    def write_matches(self, c_table_path: Path, candidates: list[MatchCandidate]) -> Path:
        workbook = self.loader.load(c_table_path)
        sheet = self.loader.active_sheet(workbook)
        header_map = self._header_map(sheet)
        row_offset = 0
        for candidate in candidates:
            target_row = candidate.a_record.row_number + row_offset
            if not candidate.b_records:
                self._write_candidate_row(sheet, header_map, target_row, candidate, None)
                continue
            for index, b_record in enumerate(candidate.b_records):
                if index > 0:
                    target_row += 1
                    sheet.insert_rows(target_row)
                    self._blank_business_columns(sheet, target_row, header_map)
                    row_offset += 1
                self._write_candidate_row(sheet, header_map, target_row, candidate, b_record)
        return self.loader.save(workbook, c_table_path)

    def _header_map(self, sheet: Worksheet) -> dict[str, int]:
        return {str(cell.value): cell.column for cell in sheet[1] if cell.value not in (None, "")}

    def _write_candidate_row(
        self,
        sheet: Worksheet,
        header_map: dict[str, int],
        row: int,
        candidate: MatchCandidate,
        b_record: BRecord | None,
    ) -> None:
        values: dict[str, Any] = {
            self.append_columns.match_status: candidate.status.value,
            self.append_columns.match_basis: candidate.basis,
            self.append_columns.match_direction: candidate.direction.value,
            self.append_columns.quantity_diff: candidate.quantity_diff,
            self.append_columns.amount_diff: candidate.amount_diff,
            self.append_columns.review_type: candidate.review_type,
            self.append_columns.handling_note: "需人工复核" if candidate.review_type else "自动承接",
        }
        if b_record:
            quantity, unit_price, amount = self._directional_values(b_record, candidate.direction)
            values.update(
                {
                    self.append_columns.b_row_number: b_record.row_number,
                    self.append_columns.warehouse: b_record.warehouse,
                    self.append_columns.system_time: b_record.system_time,
                    self.append_columns.document_no: b_record.document_no,
                    self.append_columns.product_code: b_record.product_code,
                    self.append_columns.product_name: b_record.product_name,
                    self.append_columns.spec: b_record.spec,
                    self.append_columns.b_quantity: quantity,
                    self.append_columns.b_unit_price: unit_price,
                    self.append_columns.b_amount: amount,
                }
            )
        for header, value in values.items():
            column = header_map.get(header)
            if column:
                sheet.cell(row, column, value)

    def _directional_values(self, record: BRecord, direction: MatchDirection) -> tuple[Any, Any, Any]:
        if direction == MatchDirection.INBOUND:
            return record.inbound_qty, record.inbound_unit_price, record.inbound_amount
        if direction == MatchDirection.OUTBOUND:
            return record.outbound_qty, record.outbound_unit_price, record.outbound_amount
        return None, None, None

    def _blank_business_columns(self, sheet: Worksheet, row: int, header_map: dict[str, int]) -> None:
        first_trace_column = min(header_map[header] for header in self.append_columns.__dict__.values() if header in header_map)
        for column in range(1, first_trace_column):
            sheet.cell(row, column, None)
