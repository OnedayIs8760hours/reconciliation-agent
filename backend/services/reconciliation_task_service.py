from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from fastapi import UploadFile

from backend.domain.product_mapping import ProductMappingItem, ProductMappingResult, ProductReviewItem
from backend.services.b_missing_marker_service import BMissingMarkerService
from backend.services.b_record_service import BRecordService
from backend.services.c_table_base_service import CTableBaseService
from backend.services.c_table_match_service import CTableMatchService
from backend.services.llm_agent_factory import build_deepseek_agent
from backend.services.product_mapping_service import ProductMappingLookup, ProductMappingService
from backend.services.reconciliation_verify_service import ReconciliationVerifyService
from backend.services.reverse_verify_service import ReverseVerifyService
from backend.services.sheet_structure_service import SheetStructureService
from tools import ExcelSheetPreview


class ReconciliationTaskService:
    """编排完整对账任务：上传、制表、匹配、反向核查、验收和元数据。"""

    def __init__(self, tasks_dir: Path) -> None:
        """初始化任务服务，传入任务根目录。"""

        self.tasks_dir = tasks_dir

    async def run_upload_task(self, task_id: str, a_file: UploadFile, b_file: UploadFile, month: str) -> dict[str, object]:
        """保存上传文件并执行完整正式对账流程。"""

        task_dir = self.tasks_dir / task_id
        # mkdir(...)：创建本次任务目录，所有结果文件都放在里面。
        task_dir.mkdir(parents=True, exist_ok=False)

        a_file_path = task_dir / "A.xlsx"
        b_file_path = task_dir / "B.xlsx"
        c_file_path = task_dir / "C.xlsx"
        b_marked_file_path = task_dir / "B_marked.xlsx"
        verify_report_file_path = task_dir / "verify_report.json"
        metadata_file_path = task_dir / "metadata.json"

        await self.save_upload(a_file, a_file_path)
        await self.save_upload(b_file, b_file_path)

        created_at = datetime.now().isoformat(timespec="seconds")
        status = "PROCESSING"
        verify_report_dict: dict[str, object] = {}
        exceptions: list[dict[str, object]] = []

        shared_agent = build_deepseek_agent()

        # SheetStructureService(...)：识别完整 A/B 对账字段，避免把 A 表结构写死在代码里。
        structure_service = SheetStructureService(llm_agent=shared_agent)
        a_preview, b_preview, schema_result = structure_service.analyze_structure(str(a_file_path), str(b_file_path))

        # ProductMappingService(...)：继续复用前一步商品去重和 LLM 商品规格映射结果。
        product_mapping_service = ProductMappingService(llm_agent=shared_agent)
        product_mapping = product_mapping_service.build_product_mapping(a_file_path, b_file_path)
        product_lookup = self.build_product_lookup(product_mapping)

        # CTableBaseService(...)：从 A 表完整复制生成 C 表底稿，不抽列重建。
        c_table_service = CTableBaseService()
        c_table_result = c_table_service.build_base_table(a_file_path, c_file_path, schema_result.a_schema)

        # BRecordService(...)：把 B 表入库和出库字段拆成统一记录结构。
        b_record_service = BRecordService()
        b_records = b_record_service.read_records(b_file_path, schema_result.b_schema, month)

        # CTableMatchService(...)：用 C/A 明细匹配 B 系统记录，并把追溯字段写入 C 表。
        match_service = CTableMatchService()
        match_summary = match_service.match_and_write(
            c_file_path,
            schema_result.a_schema,
            c_table_result,
            b_records,
            product_lookup,
        )

        # ReverseVerifyService(...)：核查 B 表本月记录是否全部承接或标注。
        reverse_service = ReverseVerifyService()
        reverse_summary = reverse_service.verify(b_records, match_summary)

        # BMissingMarkerService(...)：把未承接的 B 表本月记录写入 B_marked.xlsx。
        marker_service = BMissingMarkerService()
        marker_result = marker_service.mark_missing_records(
            b_file_path,
            b_marked_file_path,
            schema_result.b_schema,
            reverse_summary,
        )

        # ReconciliationVerifyService(...)：执行交付前强制验收并写 verify_report.json。
        verify_service = ReconciliationVerifyService()
        verify_report = verify_service.verify(
            a_file_path,
            c_file_path,
            b_marked_file_path,
            c_table_result,
            match_summary,
            reverse_summary,
            marker_result,
            schema_result.a_schema.quantity_field.column_index,
            schema_result.a_schema.amount_field.column_index,
            verify_report_file_path,
        )
        verify_report_dict = verify_report.to_dict()
        exceptions = list(verify_report.exceptions)

        if verify_report.passed:
            status = "SUCCESS"
        else:
            status = "FAILED"

        response = {
            "task_id": task_id,
            "status": status,
            "month": month,
            "a_preview": preview_to_response(a_preview),
            "b_preview": preview_to_response(b_preview),
            "schema_result": schema_result.to_dict(),
            "llm_result": schema_result.to_dict(),
            "product_mapping": product_mapping,
            "c_table_result": c_table_result.to_dict(),
            "b_records": [record.to_dict() for record in b_records],
            "match_summary": match_summary.to_dict(),
            "reverse_verify_summary": reverse_summary.to_dict(),
            "b_missing_marker": marker_result.to_dict(),
            "verify_report": verify_report_dict,
            "exceptions": exceptions,
            "downloads": build_downloads(task_id, status),
            "created_at": created_at,
            "completed_at": datetime.now().isoformat(timespec="seconds"),
        }

        # write_text(...)：把任务元数据写入 JSON，方便后续下载、排查和前端查询。
        metadata_file_path.write_text(json.dumps(response, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return response

    async def save_upload(self, file: UploadFile, target: Path) -> None:
        """把上传文件保存到任务目录。"""

        try:
            # await file.read()：异步读取上传文件的二进制内容。
            content = await file.read()
            if not content:
                raise ValueError(f"{file.filename} 文件内容为空")
            # write_bytes(...)：按二进制写入 Excel 文件。
            target.write_bytes(content)
        finally:
            # close()：关闭上传文件句柄，避免临时资源泄漏。
            await file.close()

    def build_product_lookup(self, product_mapping: dict[str, object]) -> ProductMappingLookup:
        """把商品映射接口结果还原成匹配服务可用的查询表。"""

        result_payload = product_mapping.get("result")
        if not isinstance(result_payload, dict):
            return ProductMappingLookup(ProductMappingResult())

        mapping_items: list[ProductMappingItem] = []
        mappings = result_payload.get("mappings")
        if isinstance(mappings, list):
            for item in mappings:
                if not isinstance(item, dict):
                    continue
                standard = text_value(item.get("standard"))
                a_value = text_value(item.get("a_value"))
                b_value = text_value(item.get("b_value"))
                if not standard or not a_value or not b_value:
                    continue
                mapping_items.append(
                    ProductMappingItem(
                        standard=standard,
                        a_value=a_value,
                        b_value=b_value,
                        confidence=float_value(item.get("confidence")),
                        reason=text_value(item.get("reason")),
                    )
                )

        review_items: list[ProductReviewItem] = []
        reviews = result_payload.get("need_review")
        if isinstance(reviews, list):
            for item in reviews:
                if not isinstance(item, dict):
                    continue
                review_items.append(
                    ProductReviewItem(
                        a_value=text_value(item.get("a_value")),
                        b_value=text_value(item.get("b_value")),
                        confidence=float_value(item.get("confidence")),
                        reason=text_value(item.get("reason")),
                    )
                )

        mapping_result = ProductMappingResult(
            mappings=mapping_items,
            unmatched_a=string_list(result_payload.get("unmatched_a")),
            unmatched_b=string_list(result_payload.get("unmatched_b")),
            need_review=review_items,
        )
        return ProductMappingLookup(mapping_result)


def preview_to_response(preview: ExcelSheetPreview) -> dict[str, object]:
    """把 Excel 预览转成前端和 metadata 都能直接使用的字典。"""

    return {
        "sheet_name": preview.sheet_name,
        "max_row": preview.max_row,
        "max_column": preview.max_column,
        "rows": [
            {
                "row_number": row.row_number,
                "cells": [
                    {
                        "coordinate": cell.coordinate,
                        "column": cell.column,
                        "value": cell.display_text,
                        "python_type": cell.python_type,
                        "excel_data_type": cell.excel_data_type,
                        "number_format": cell.number_format,
                        "is_date": cell.is_date,
                    }
                    for cell in row.cells
                ],
            }
            for row in preview.rows
        ],
    }


def build_downloads(task_id: str, status: str) -> list[dict[str, object]]:
    """构建前端下载文件列表。"""

    enabled = status == "SUCCESS" or status == "FAILED"
    return [
        {
            "id": "c-table",
            "name": "C表.xlsx",
            "type": "excel",
            "enabled": enabled,
            "url": f"/api/reconciliation/tasks/{task_id}/files/c-table",
        },
        {
            "id": "b-marked",
            "name": "B表缺失标注.xlsx",
            "type": "excel",
            "enabled": enabled,
            "url": f"/api/reconciliation/tasks/{task_id}/files/b-marked",
        },
        {
            "id": "verify-report",
            "name": "核查报告.json",
            "type": "report",
            "enabled": enabled,
            "url": f"/api/reconciliation/tasks/{task_id}/files/verify-report",
        },
    ]


def text_value(value: object) -> str:
    """把任意值安全转换成文本。"""

    if value is None:
        return ""
    return str(value).strip()


def float_value(value: object) -> float:
    """把任意值安全转换成小数。"""

    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def string_list(value: object) -> list[str]:
    """把列表值安全转换成字符串列表。"""

    result: list[str] = []
    if not isinstance(value, list):
        return result
    for item in value:
        text = text_value(item)
        if text:
            result.append(text)
    return result
