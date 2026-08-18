"""将 A/B 工作簿行解析为领域记录。"""

from decimal import Decimal
from pathlib import Path

from agent.core.normalizer import Normalizer
from agent.core.workbook_loader import WorkbookLoader
from agent.domain.records import ARecord, BRecord
from agent.domain.schemas import BTableColumns


class RecordExtractor:
    """提取领域记录，同时保留原始工作簿值以便追溯。"""

    def __init__(self, loader: WorkbookLoader, normalizer: Normalizer) -> None:
        self.loader = loader
        self.normalizer = normalizer
        self.b_columns = BTableColumns()

    def extract_a_records(self, path: Path) -> list[ARecord]:
        """使用常见首个工作表约定提取 A 表业务行。"""
        workbook = self.loader.load(path, data_only=False)
        sheet = self.loader.active_sheet(workbook)
        records: list[ARecord] = []
        for row_number, values in self.loader.iter_data_rows(sheet):
            quantity = self.normalizer.decimal_value(values[5] if len(values) > 5 else None)
            amount = self.normalizer.decimal_value(values[7] if len(values) > 7 else None)
            records.append(
                ARecord(
                    row_number=row_number,
                    display_date=self.normalizer.text_value(values[0] if values else None),
                    normalized_date=self.normalizer.date_value(values[0] if values else None),
                    document_no=self.normalizer.text_value(values[1] if len(values) > 1 else None),
                    product_name=self.normalizer.text_value(values[2] if len(values) > 2 else None),
                    normalized_spec=self.normalizer.spec_value(values[3] if len(values) > 3 else None),
                    unit=self.normalizer.text_value(values[4] if len(values) > 4 else None),
                    quantity=quantity,
                    unit_price=self.normalizer.decimal_value(values[6] if len(values) > 6 else None),
                    amount=amount,
                    remark=self.normalizer.text_value(values[8] if len(values) > 8 else None),
                    raw_values={str(i + 1): value for i, value in enumerate(values)},
                )
            )
        return records

    def extract_b_records(self, path: Path) -> list[BRecord]:
        """使用固定的 E:P 列定义提取 B 表系统行。"""
        workbook = self.loader.load(path, data_only=False)
        sheet = self.loader.active_sheet(workbook)
        records: list[BRecord] = []
        for row_number, _values in self.loader.iter_data_rows(sheet):
            get = lambda index: sheet.cell(row_number, index).value
            system_time = self.normalizer.datetime_value(get(self.b_columns.system_time))
            records.append(
                BRecord(
                    row_number=row_number,
                    warehouse=self.normalizer.text_value(get(self.b_columns.warehouse)),
                    system_time=system_time,
                    system_date=system_time.date() if system_time else None,
                    document_no=self.normalizer.text_value(get(self.b_columns.document_no)),
                    product_code=self.normalizer.text_value(get(self.b_columns.product_code)),
                    product_name=self.normalizer.text_value(get(self.b_columns.product_name)),
                    spec=self.normalizer.text_value(get(self.b_columns.spec)),
                    normalized_spec=self.normalizer.spec_value(get(self.b_columns.spec)),
                    inbound_qty=self._positive_decimal(get(self.b_columns.inbound_qty)),
                    inbound_unit_price=self.normalizer.decimal_value(get(self.b_columns.inbound_unit_price)),
                    inbound_amount=self.normalizer.decimal_value(get(self.b_columns.inbound_amount)),
                    outbound_qty=self._positive_decimal(get(self.b_columns.outbound_qty)),
                    outbound_unit_price=self.normalizer.decimal_value(get(self.b_columns.outbound_unit_price)),
                    outbound_amount=self.normalizer.decimal_value(get(self.b_columns.outbound_amount)),
                )
            )
        return records

    def _positive_decimal(self, value: object) -> Decimal | None:
        decimal = self.normalizer.decimal_value(value)
        if decimal is None or decimal == 0:
            return None
        return abs(decimal)
