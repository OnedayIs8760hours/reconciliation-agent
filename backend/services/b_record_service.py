from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from backend.domain.reconciliation_record import BTableRecord
from backend.domain.reconciliation_schema import BSheetFieldSchema
from tools import excel_tool


class BRecordService:
    """读取 B 表系统出入库明细，并转换成统一记录结构。"""

    def read_records(self, b_file_path: Path, b_schema: BSheetFieldSchema, month: str) -> list[BTableRecord]:
        """按字段结构读取 B 表记录，入库和出库统一成 direction 结构。"""

        workbook = excel_tool.load_workbook(b_file_path, data_only=True)
        worksheet = excel_tool.get_sheet(workbook, b_schema.sheet_name or None)

        records: list[BTableRecord] = []
        for row_index in range(b_schema.detail_start_row, b_schema.detail_end_row + 1):
            inbound_record = self.build_record(worksheet, row_index, b_schema, month, direction="入库")
            if inbound_record is not None:
                records.append(inbound_record)

            outbound_record = self.build_record(worksheet, row_index, b_schema, month, direction="出库")
            if outbound_record is not None:
                records.append(outbound_record)

        return records

    def build_record(
        self,
        worksheet: Any,
        row_index: int,
        b_schema: BSheetFieldSchema,
        month: str,
        *,
        direction: str,
    ) -> BTableRecord | None:
        """把 B 表一行中的入库或出库字段转换成标准记录。"""

        if direction == "入库":
            quantity = to_float(self.get_cell_value(worksheet, row_index, b_schema.inbound_quantity_field.column_index))
            unit_price = to_float(self.get_cell_value(worksheet, row_index, b_schema.inbound_unit_price_field.column_index))
            amount = to_float(self.get_cell_value(worksheet, row_index, b_schema.inbound_amount_field.column_index))
        else:
            quantity = to_float(self.get_cell_value(worksheet, row_index, b_schema.outbound_quantity_field.column_index))
            unit_price = to_float(self.get_cell_value(worksheet, row_index, b_schema.outbound_unit_price_field.column_index))
            amount = to_float(self.get_cell_value(worksheet, row_index, b_schema.outbound_amount_field.column_index))

        if quantity == 0 and unit_price == 0 and amount == 0:
            return None

        system_time = self.get_cell_value(worksheet, row_index, b_schema.system_time_field.column_index)
        risk_note = ""
        if quantity == 0 or amount == 0:
            risk_note = "零数量或零金额需复核"

        return BTableRecord(
            source_row=row_index,
            direction=direction,
            warehouse=to_text(self.get_cell_value(worksheet, row_index, b_schema.warehouse_field.column_index)),
            system_time=system_time,
            document_no=to_text(self.get_cell_value(worksheet, row_index, b_schema.document_no_field.column_index)),
            sku=to_text(self.get_cell_value(worksheet, row_index, b_schema.sku_field.column_index)),
            product_name=to_text(self.get_cell_value(worksheet, row_index, b_schema.product_name_field.column_index)),
            spec=excel_tool.clean_product_text(self.get_cell_value(worksheet, row_index, b_schema.spec_field.column_index)),
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
            is_current_month=is_current_month(system_time, month),
            risk_note=risk_note,
        )

    def get_cell_value(self, worksheet: Any, row_index: int, column_index: int) -> object:
        """安全读取单元格值，列号无效时返回空。"""

        if column_index < 1:
            return None
        # cell(...)：用数字行列读取单元格，比列字母更适合 LLM 返回的结构化列号。
        return worksheet.cell(row=row_index, column=column_index).value


def to_float(value: object) -> float:
    """把 Excel 单元格值安全转换成数字。"""

    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def to_text(value: object) -> str:
    """把 Excel 单元格值安全转换成文本。"""

    if value is None:
        return ""
    return str(value).strip()


def is_current_month(value: object, month: str) -> bool:
    """判断日期值是否属于当前对账月份，month 格式为 YYYY-MM。"""

    if value is None:
        return False
    if isinstance(value, datetime):
        return value.strftime("%Y-%m") == month
    if isinstance(value, date):
        return value.strftime("%Y-%m") == month

    text = str(value).strip()
    return text.startswith(month)
