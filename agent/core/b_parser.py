"""B 表解析。"""

from __future__ import annotations

from datetime import datetime

from agent.core.normalizer import month_key, normalize_date_key, normalize_spec, normalize_text, to_decimal
from agent.core.workbook_profiler import SheetProfile
from agent.domain.records import BRecord
from agent.domain.statuses import Direction


class BParser:
    def parse(self, worksheet, profile: SheetProfile, month: str) -> list[BRecord]:
        records: list[BRecord] = []
        columns = profile.columns
        for row in range(profile.header_row + 1, worksheet.max_row + 1):
            system_time = self._value(worksheet, row, columns.get("system_time") or columns.get("date"))
            if system_time and month_key(system_time) != month:
                continue
            common = {
                "warehouse": normalize_text(self._value(worksheet, row, columns.get("warehouse"))),
                "system_time": system_time,
                "date_key": normalize_date_key(system_time or self._value(worksheet, row, columns.get("date"))),
                "document_no": normalize_text(self._value(worksheet, row, columns.get("document_no"))),
                "item_code": normalize_text(self._value(worksheet, row, columns.get("item_code"))),
                "item_name": normalize_text(self._value(worksheet, row, columns.get("item_name"))),
                "spec_raw": normalize_text(self._value(worksheet, row, columns.get("spec"))),
                "spec_key": normalize_spec(self._value(worksheet, row, columns.get("spec"))),
            }
            in_qty = to_decimal(self._value(worksheet, row, columns.get("in_qty") or columns.get("qty")))
            in_amount = to_decimal(self._value(worksheet, row, columns.get("in_amount") or columns.get("amount")))
            out_qty = to_decimal(self._value(worksheet, row, columns.get("out_qty")))
            out_amount = to_decimal(self._value(worksheet, row, columns.get("out_amount")))
            if in_qty != 0 or in_amount != 0:
                records.append(self._record(worksheet, row, Direction.INBOUND, in_qty, in_amount, columns.get("in_price") or columns.get("price"), common))
            if out_qty != 0 or out_amount != 0:
                records.append(self._record(worksheet, row, Direction.OUTBOUND, abs(out_qty), abs(out_amount), columns.get("out_price"), common))
        return records

    def _record(self, worksheet, row: int, direction: Direction, qty, amount, price_column, common) -> BRecord:
        system_time = common["system_time"]
        if isinstance(system_time, datetime):
            system_time_value = system_time
        else:
            system_time_value = str(system_time) if system_time else None
        return BRecord(
            record_id=f"B{row}-{direction.value}",
            row=row,
            direction=direction,
            warehouse=common["warehouse"],
            system_time=system_time_value,
            date_key=common["date_key"],
            document_no=common["document_no"],
            item_code=common["item_code"],
            item_name=common["item_name"],
            spec_raw=common["spec_raw"],
            spec_key=common["spec_key"],
            qty=qty,
            price=to_decimal(self._value(worksheet, row, price_column)),
            amount=amount,
            raw_fields={str(column): worksheet.cell(row=row, column=column).value for column in range(1, worksheet.max_column + 1)},
        )

    @staticmethod
    def _value(worksheet, row: int, column: int | None):
        return worksheet.cell(row=row, column=column).value if column else None
