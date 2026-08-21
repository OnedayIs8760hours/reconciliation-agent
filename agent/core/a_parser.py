"""A 表解析。"""

from __future__ import annotations

from agent.core.normalizer import normalize_date_key, normalize_spec, normalize_text, to_decimal
from agent.core.workbook_profiler import SheetProfile
from agent.domain.records import ADetailRow
from agent.domain.statuses import Direction


class AParser:
    def parse(self, worksheet, profile: SheetProfile) -> list[ADetailRow]:
        records: list[ADetailRow] = []
        columns = profile.columns
        for row in range(profile.header_row + 1, worksheet.max_row + 1):
            qty = to_decimal(self._value(worksheet, row, columns.get("qty")))
            amount = to_decimal(self._value(worksheet, row, columns.get("amount")))
            if qty == 0 and amount == 0 and not self._row_has_value(worksheet, row):
                continue
            item_name = normalize_text(self._value(worksheet, row, columns.get("item_name")))
            document_no = normalize_text(self._value(worksheet, row, columns.get("document_no")))
            if not item_name and not document_no and qty == 0 and amount == 0:
                continue
            direction = Direction.INBOUND if qty > 0 else Direction.OUTBOUND if qty < 0 else Direction.UNKNOWN
            raw_values = {str(column): worksheet.cell(row=row, column=column).value for column in range(1, worksheet.max_column + 1)}
            records.append(
                ADetailRow(
                    row=row,
                    date_key=normalize_date_key(self._value(worksheet, row, columns.get("date"))),
                    document_no=document_no,
                    item_code=normalize_text(self._value(worksheet, row, columns.get("item_code"))),
                    item_name=item_name,
                    spec_raw=normalize_text(self._value(worksheet, row, columns.get("spec"))),
                    spec_key=normalize_spec(self._value(worksheet, row, columns.get("spec"))),
                    qty=qty,
                    price=to_decimal(self._value(worksheet, row, columns.get("price"))),
                    amount=amount,
                    direction=direction,
                    raw_values=raw_values,
                )
            )
        return records

    @staticmethod
    def _value(worksheet, row: int, column: int | None):
        return worksheet.cell(row=row, column=column).value if column else None

    @staticmethod
    def _row_has_value(worksheet, row: int) -> bool:
        return any(worksheet.cell(row=row, column=column).value not in (None, "") for column in range(1, worksheet.max_column + 1))
