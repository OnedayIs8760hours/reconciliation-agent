from __future__ import annotations

from pathlib import Path

from agent.llm import ReconciliationLLMAgent
from backend.domain.json_parser import parse_json_object
from backend.domain.product_mapping import ProductStructureResult
from backend.domain.product_mapping_parser import parse_field_guess, parse_product_mapping_result
from backend.domain.product_mapping_projection import build_a_b_intersection
from backend.services.product_mapping_batcher import (
    PRODUCT_MAPPING_BATCH_SIZE,
    ProductMappingBatchAnalyzer,
    chunk_list,
)
from tools import excel_tool

__all__ = [
    "PRODUCT_MAPPING_BATCH_SIZE",
    "ProductMappingService",
    "build_a_b_intersection",
    "chunk_list",
    "parse_json_object",
    "parse_product_mapping_result",
]


class ProductMappingService:
    """商品规格去重与公共信息提取服务。"""

    def __init__(self, llm_agent: ReconciliationLLMAgent | None = None) -> None:
        """初始化服务，允许测试时传入假的 LLM Agent。"""

        self.llm_agent = llm_agent or ReconciliationLLMAgent(provider="deepseek")
        self.batch_analyzer = ProductMappingBatchAnalyzer(self.llm_agent)

    def build_product_mapping(
        self,
        a_file_path: Path,
        b_file_path: Path,
        *,
        a_sheet_name: str | None = None,
        b_sheet_name: str | None = None,
        preview_rows: int | None = None,
    ) -> dict[str, object]:
        """先识别 A/B 表商品字段，再读取商品列并生成映射结果。"""

        preview_row_count = preview_rows or 20
        a_preview = excel_tool.read_sheet_preview(
            a_file_path,
            sheet_name=a_sheet_name,
            rows=preview_row_count,
        )
        b_preview = excel_tool.read_sheet_preview(
            b_file_path,
            sheet_name=b_sheet_name,
            rows=preview_row_count,
        )

        structure_result = self.guess_product_fields(a_preview, b_preview)
        self.validate_structure_result(structure_result)

        a_unique = self.read_unique_product_values(
            a_file_path,
            structure_result.a_sheet.field_name,
            sheet_name=a_sheet_name,
            header_row=structure_result.a_sheet.header_row_guess,
        )
        b_unique = self.read_unique_product_values(
            b_file_path,
            structure_result.b_sheet.field_name,
            sheet_name=b_sheet_name,
            header_row=structure_result.b_sheet.header_row_guess,
        )

        mapping_result, llm_model, llm_provider = self.analyze_product_mapping_in_batches(
            a_unique,
            b_unique,
        )
        a_b_intersection = build_a_b_intersection(a_unique, b_unique, mapping_result)

        return {
            "structure": structure_result.to_dict(),
            "a_column_name": structure_result.a_sheet.field_name,
            "b_column_name": structure_result.b_sheet.field_name,
            "a_unique": a_unique,
            "b_unique": b_unique,
            "a_b_intersection": a_b_intersection,
            "llm_model": llm_model,
            "llm_provider": llm_provider,
            "result": mapping_result.to_dict(),
            "summary": {
                "a_unique_count": len(a_unique),
                "b_unique_count": len(b_unique),
                "mapping_count": mapping_result.mapping_count,
                "unmatched_a_count": len(mapping_result.unmatched_a),
                "unmatched_b_count": len(mapping_result.unmatched_b),
                "need_review_count": mapping_result.review_count,
            },
        }

    def analyze_product_mapping_in_batches(
        self,
        a_unique: list[str],
        b_unique: list[str],
        *,
        batch_size: int = PRODUCT_MAPPING_BATCH_SIZE,
    ):
        """兼容旧调用路径，实际分批逻辑位于 ProductMappingBatchAnalyzer。"""

        return self.batch_analyzer.analyze(a_unique, b_unique, batch_size=batch_size)

    def read_unique_product_values(
        self,
        file_path: Path,
        column_name: str,
        *,
        sheet_name: str | None = None,
        header_row: int = 1,
    ) -> list[str]:
        """读取商品列，并应用商品匹配所需的文本清洗和去重规则。"""

        values = excel_tool.get_column_values(
            file_path,
            column_name,
            sheet_name=sheet_name,
            header_row=header_row,
        )
        return excel_tool.unique_product_values(values)

    def guess_product_fields(
        self,
        a_preview: object,
        b_preview: object,
    ) -> ProductStructureResult:
        """让 LLM 根据表结构识别 A/B 商品字段。"""

        try:
            llm_response = self.llm_agent.analyze_sheet_structure(a_preview, b_preview)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001
            return ProductStructureResult(parse_error=str(exc))

        payload = parse_json_object(llm_response.text)
        if payload is None:
            return ProductStructureResult(raw_text=llm_response.text, parse_error="LLM 返回内容不是合法 JSON")

        return ProductStructureResult(
            a_sheet=parse_field_guess(payload.get("a_sheet")),
            b_sheet=parse_field_guess(payload.get("b_sheet")),
            raw_text=llm_response.text,
        )

    def validate_structure_result(self, structure_result: ProductStructureResult) -> None:
        """检查 LLM 是否成功识别出 A/B 表商品字段。"""

        if structure_result.parse_error:
            raise ValueError(f"商品字段结构识别失败：{structure_result.parse_error}")

        if not structure_result.a_sheet.field_name:
            raise ValueError("LLM 没有识别出 A 表商品字段，请检查 A 表表头是否清晰")

        if not structure_result.b_sheet.field_name:
            raise ValueError("LLM 没有识别出 B 表商品字段，请检查 B 表表头是否清晰")


product_mapping_service = ProductMappingService()
