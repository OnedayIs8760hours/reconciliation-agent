from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldLocation:
    """LLM 识别出来的单个字段位置。"""

    field_name: str = ""
    column_index: int = 0
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        """把字段位置转成可以写入 JSON 的字典。"""

        return {
            "field_name": self.field_name,
            "column_index": self.column_index,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SheetFieldSchema:
    """一张表的对账字段识别结果。"""

    sheet_name: str = ""
    header_row: int = 1
    detail_start_row: int = 2
    detail_end_row: int = 2
    date_field: FieldLocation = field(default_factory=FieldLocation)
    product_field: FieldLocation = field(default_factory=FieldLocation)
    quantity_field: FieldLocation = field(default_factory=FieldLocation)
    unit_price_field: FieldLocation = field(default_factory=FieldLocation)
    amount_field: FieldLocation = field(default_factory=FieldLocation)
    document_no_field: FieldLocation = field(default_factory=FieldLocation)
    unit_field: FieldLocation = field(default_factory=FieldLocation)
    remark_field: FieldLocation = field(default_factory=FieldLocation)

    def to_dict(self) -> dict[str, object]:
        """把整张表字段结构转成 JSON 字典。"""

        return {
            "sheet_name": self.sheet_name,
            "header_row": self.header_row,
            "detail_start_row": self.detail_start_row,
            "detail_end_row": self.detail_end_row,
            "date_field": self.date_field.to_dict(),
            "product_field": self.product_field.to_dict(),
            "quantity_field": self.quantity_field.to_dict(),
            "unit_price_field": self.unit_price_field.to_dict(),
            "amount_field": self.amount_field.to_dict(),
            "document_no_field": self.document_no_field.to_dict(),
            "unit_field": self.unit_field.to_dict(),
            "remark_field": self.remark_field.to_dict(),
        }


@dataclass(frozen=True)
class BSheetFieldSchema:
    """B 表系统出入库字段识别结果。"""

    sheet_name: str = ""
    header_row: int = 1
    detail_start_row: int = 2
    detail_end_row: int = 2
    warehouse_field: FieldLocation = field(default_factory=FieldLocation)
    system_time_field: FieldLocation = field(default_factory=FieldLocation)
    document_no_field: FieldLocation = field(default_factory=FieldLocation)
    sku_field: FieldLocation = field(default_factory=FieldLocation)
    product_name_field: FieldLocation = field(default_factory=FieldLocation)
    spec_field: FieldLocation = field(default_factory=FieldLocation)
    inbound_quantity_field: FieldLocation = field(default_factory=FieldLocation)
    inbound_unit_price_field: FieldLocation = field(default_factory=FieldLocation)
    inbound_amount_field: FieldLocation = field(default_factory=FieldLocation)
    outbound_quantity_field: FieldLocation = field(default_factory=FieldLocation)
    outbound_unit_price_field: FieldLocation = field(default_factory=FieldLocation)
    outbound_amount_field: FieldLocation = field(default_factory=FieldLocation)

    def to_dict(self) -> dict[str, object]:
        """把 B 表字段结构转成 JSON 字典。"""

        return {
            "sheet_name": self.sheet_name,
            "header_row": self.header_row,
            "detail_start_row": self.detail_start_row,
            "detail_end_row": self.detail_end_row,
            "warehouse_field": self.warehouse_field.to_dict(),
            "system_time_field": self.system_time_field.to_dict(),
            "document_no_field": self.document_no_field.to_dict(),
            "sku_field": self.sku_field.to_dict(),
            "product_name_field": self.product_name_field.to_dict(),
            "spec_field": self.spec_field.to_dict(),
            "inbound_quantity_field": self.inbound_quantity_field.to_dict(),
            "inbound_unit_price_field": self.inbound_unit_price_field.to_dict(),
            "inbound_amount_field": self.inbound_amount_field.to_dict(),
            "outbound_quantity_field": self.outbound_quantity_field.to_dict(),
            "outbound_unit_price_field": self.outbound_unit_price_field.to_dict(),
            "outbound_amount_field": self.outbound_amount_field.to_dict(),
        }


@dataclass(frozen=True)
class ReconciliationSchemaResult:
    """A/B 表完整对账字段结构识别结果。"""

    a_schema: SheetFieldSchema = field(default_factory=SheetFieldSchema)
    b_schema: BSheetFieldSchema = field(default_factory=BSheetFieldSchema)
    raw_text: str = ""
    parse_error: str = ""

    def to_dict(self) -> dict[str, object]:
        """把完整结构识别结果转成 JSON 字典。"""

        payload: dict[str, object] = {
            "a_schema": self.a_schema.to_dict(),
            "b_schema": self.b_schema.to_dict(),
        }
        if self.raw_text:
            payload["raw_text"] = self.raw_text
        if self.parse_error:
            payload["parse_error"] = self.parse_error
        return payload
