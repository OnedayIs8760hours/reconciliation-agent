from __future__ import annotations

import json
from typing import Any

from agent.llm import ReconciliationLLMAgent
from backend.domain.reconciliation_schema import (
    BSheetFieldSchema,
    FieldLocation,
    ReconciliationSchemaResult,
    SheetFieldSchema,
)
from backend.services.product_mapping_service import parse_json_object, safe_float, safe_int, safe_string
from tools import ExcelSheetPreview, excel_tool


class SheetStructureService:
    """A/B 表完整对账字段结构识别服务。"""

    def __init__(self, llm_agent: ReconciliationLLMAgent | None = None) -> None:
        """初始化字段识别服务，测试时可以传入假的 LLM。"""

        if llm_agent is None:
            llm_agent = ReconciliationLLMAgent(provider="deepseek")
        self.llm_agent = llm_agent

    def analyze_structure(
        self,
        a_file_path: str,
        b_file_path: str,
        *,
        a_sheet_name: str | None = None,
        b_sheet_name: str | None = None,
    ) -> tuple[ExcelSheetPreview, ExcelSheetPreview, ReconciliationSchemaResult]:
        """读取 A/B 表完整预览，并调用 LLM 识别对账字段。"""

        # read_sheet_preview(..., rows=None)：读取工作表全部行和全部列，避免只看前几列导致字段遗漏。
        a_preview = excel_tool.read_sheet_preview(a_file_path, sheet_name=a_sheet_name, rows=None)
        b_preview = excel_tool.read_sheet_preview(b_file_path, sheet_name=b_sheet_name, rows=None)

        result = self.guess_reconciliation_schema(a_preview, b_preview)
        self.validate_schema_result(result)
        return a_preview, b_preview, result

    def guess_reconciliation_schema(
        self,
        a_preview: ExcelSheetPreview,
        b_preview: ExcelSheetPreview,
    ) -> ReconciliationSchemaResult:
        """让 LLM 根据完整结构预览识别 A/B 对账字段。"""

        try:
            llm_response = self.llm_agent.analyze_reconciliation_structure(a_preview, b_preview)
        except Exception as exc:
            return ReconciliationSchemaResult(parse_error=str(exc))

        payload = parse_json_object(llm_response.text)
        if payload is None:
            return ReconciliationSchemaResult(raw_text=llm_response.text, parse_error="LLM 返回内容不是合法 JSON")

        a_schema = parse_a_schema(payload.get("a_schema"), default_sheet_name=a_preview.sheet_name, max_row=a_preview.max_row)
        b_schema = parse_b_schema(payload.get("b_schema"), default_sheet_name=b_preview.sheet_name, max_row=b_preview.max_row)
        return ReconciliationSchemaResult(a_schema=a_schema, b_schema=b_schema, raw_text=llm_response.text)

    def validate_schema_result(self, result: ReconciliationSchemaResult) -> None:
        """检查正式对账流程必需字段是否识别完整。"""

        if result.parse_error:
            raise ValueError(f"对账字段结构识别失败：{result.parse_error}")

        required_a_fields = {
            "A表日期字段": result.a_schema.date_field,
            "A表商品字段": result.a_schema.product_field,
            "A表数量字段": result.a_schema.quantity_field,
            "A表金额字段": result.a_schema.amount_field,
        }
        for label, field in required_a_fields.items():
            if not field.field_name or field.column_index < 1:
                raise ValueError(f"LLM 没有识别出{label}，不能生成正式 C 表")

        required_b_fields = {
            "B表系统时间字段": result.b_schema.system_time_field,
            "B表规格字段": result.b_schema.spec_field,
            "B表入库数量字段": result.b_schema.inbound_quantity_field,
            "B表出库数量字段": result.b_schema.outbound_quantity_field,
        }
        for label, field in required_b_fields.items():
            if not field.field_name or field.column_index < 1:
                raise ValueError(f"LLM 没有识别出{label}，不能执行 B 表反向核查")


def parse_field_location(value: object) -> FieldLocation:
    """解析 LLM 返回的字段位置对象。"""

    if not isinstance(value, dict):
        return FieldLocation()

    field_name = safe_string(value.get("field_name"))
    column_index = safe_int(value.get("column_index"), default=0)
    confidence = safe_float(value.get("confidence"))
    reason = safe_string(value.get("reason"))

    if column_index < 0:
        column_index = 0

    return FieldLocation(field_name=field_name, column_index=column_index, confidence=confidence, reason=reason)


def parse_a_schema(value: object, *, default_sheet_name: str, max_row: int) -> SheetFieldSchema:
    """解析 A 表结构识别结果。"""

    if not isinstance(value, dict):
        return SheetFieldSchema(sheet_name=default_sheet_name, detail_end_row=max_row)

    header_row = safe_int(value.get("header_row"), default=1)
    detail_start_row = safe_int(value.get("detail_start_row"), default=header_row + 1)
    detail_end_row = safe_int(value.get("detail_end_row"), default=max_row)

    if header_row < 1:
        header_row = 1
    if detail_start_row < header_row + 1:
        detail_start_row = header_row + 1
    if detail_end_row < detail_start_row:
        detail_end_row = max_row

    return SheetFieldSchema(
        sheet_name=safe_string(value.get("sheet_name")) or default_sheet_name,
        header_row=header_row,
        detail_start_row=detail_start_row,
        detail_end_row=detail_end_row,
        date_field=parse_field_location(value.get("date_field")),
        product_field=parse_field_location(value.get("product_field")),
        quantity_field=parse_field_location(value.get("quantity_field")),
        unit_price_field=parse_field_location(value.get("unit_price_field")),
        amount_field=parse_field_location(value.get("amount_field")),
        document_no_field=parse_field_location(value.get("document_no_field")),
        unit_field=parse_field_location(value.get("unit_field")),
        remark_field=parse_field_location(value.get("remark_field")),
    )


def parse_b_schema(value: object, *, default_sheet_name: str, max_row: int) -> BSheetFieldSchema:
    """解析 B 表结构识别结果。"""

    if not isinstance(value, dict):
        return BSheetFieldSchema(sheet_name=default_sheet_name, detail_end_row=max_row)

    header_row = safe_int(value.get("header_row"), default=1)
    detail_start_row = safe_int(value.get("detail_start_row"), default=header_row + 1)
    detail_end_row = safe_int(value.get("detail_end_row"), default=max_row)

    if header_row < 1:
        header_row = 1
    if detail_start_row < header_row + 1:
        detail_start_row = header_row + 1
    if detail_end_row < detail_start_row:
        detail_end_row = max_row

    return BSheetFieldSchema(
        sheet_name=safe_string(value.get("sheet_name")) or default_sheet_name,
        header_row=header_row,
        detail_start_row=detail_start_row,
        detail_end_row=detail_end_row,
        warehouse_field=parse_field_location(value.get("warehouse_field")),
        system_time_field=parse_field_location(value.get("system_time_field")),
        document_no_field=parse_field_location(value.get("document_no_field")),
        sku_field=parse_field_location(value.get("sku_field")),
        product_name_field=parse_field_location(value.get("product_name_field")),
        spec_field=parse_field_location(value.get("spec_field")),
        inbound_quantity_field=parse_field_location(value.get("inbound_quantity_field")),
        inbound_unit_price_field=parse_field_location(value.get("inbound_unit_price_field")),
        inbound_amount_field=parse_field_location(value.get("inbound_amount_field")),
        outbound_quantity_field=parse_field_location(value.get("outbound_quantity_field")),
        outbound_unit_price_field=parse_field_location(value.get("outbound_unit_price_field")),
        outbound_amount_field=parse_field_location(value.get("outbound_amount_field")),
    )


def schema_to_json(result: ReconciliationSchemaResult) -> str:
    """把字段结构识别结果格式化成 JSON 文本。"""

    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str)
