from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.llm import ReconciliationLLMAgent
from backend.domain.product_mapping import (
    ProductFieldGuess,
    ProductMappingItem,
    ProductMappingResult,
    ProductReviewItem,
    ProductStructureResult,
)
from tools import excel_tool


class ProductMappingService:
    """商品规格去重与公共信息提取服务。"""

    def __init__(self, llm_agent: ReconciliationLLMAgent | None = None) -> None:
        """初始化服务，允许测试时传入假的 LLM Agent。"""

        if llm_agent is None:
            # ReconciliationLLMAgent(...)：创建默认 LLM Agent，具体模型由配置决定。
            llm_agent = ReconciliationLLMAgent(provider="deepseek")
        self.llm_agent = llm_agent

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

        # 脚本提取唯一值列
        a_unique = excel_tool.get_unique_column_values(
            a_file_path,
            structure_result.a_sheet.field_name,
            sheet_name=a_sheet_name,
            header_row=structure_result.a_sheet.header_row_guess,
        )
        b_unique = excel_tool.get_unique_column_values(
            b_file_path,
            structure_result.b_sheet.field_name,
            sheet_name=b_sheet_name,
            header_row=structure_result.b_sheet.header_row_guess,
        )
        # analyze_product_mapping(...)：把去重后的商品列表交给 LLM 做语义匹配。
        llm_response = self.llm_agent.analyze_product_mapping(a_unique, b_unique)
        
        mapping_result = parse_product_mapping_result(llm_response.text)
        # 从 LLM 返回的 mappings 字段生成 A/B 匹配结果。
        a_b_intersection = build_a_b_intersection(a_unique, b_unique, mapping_result)

        return {
            "structure": structure_result.to_dict(),
            "a_column_name": structure_result.a_sheet.field_name,
            "b_column_name": structure_result.b_sheet.field_name,
            "a_unique": a_unique,
            "b_unique": b_unique,
            "a_b_intersection": a_b_intersection,
            "llm_model": llm_response.model,
            "llm_provider": llm_response.provider,
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

    def guess_product_fields(
        self,
        a_preview: object,
        b_preview: object,
    ) -> ProductStructureResult:
        """让 LLM 根据表结构识别 A/B 商品字段。"""

        if not isinstance(a_preview, object) or not isinstance(b_preview, object):
            return ProductStructureResult(parse_error="预览数据无效")

        try:
            llm_response = self.llm_agent.analyze_sheet_structure(a_preview, b_preview)  # type: ignore[arg-type]
        except Exception as exc:
            return ProductStructureResult(parse_error=str(exc))

        
        
        # 把LLM 的回答解析成 JSON 对象，方便后续提取字段信息。
        payload = parse_json_object(llm_response.text)
        if payload is None:
            return ProductStructureResult(raw_text=llm_response.text, parse_error="LLM 返回内容不是合法 JSON")

        # 从 JSON 对象中提取 A 表的字段识别结果。
        a_sheet = parse_field_guess(payload.get("a_sheet"))
        # 从 JSON 对象中提取 B 表的字段识别结果。
        b_sheet = parse_field_guess(payload.get("b_sheet"))
        return ProductStructureResult(a_sheet=a_sheet, b_sheet=b_sheet, raw_text=llm_response.text)

    def validate_structure_result(self, structure_result: ProductStructureResult) -> None:
        """检查 LLM 是否成功识别出 A/B 表商品字段。"""

        if structure_result.parse_error:
            raise ValueError(f"商品字段结构识别失败：{structure_result.parse_error}")

        if not structure_result.a_sheet.field_name:
            raise ValueError("LLM 没有识别出 A 表商品字段，请检查 A 表表头是否清晰")

        if not structure_result.b_sheet.field_name:
            raise ValueError("LLM 没有识别出 B 表商品字段，请检查 B 表表头是否清晰")



def parse_field_guess(value: object) -> ProductFieldGuess:
    """解析 LLM 返回的单个表商品字段识别结果。"""

    if not isinstance(value, dict):
        return ProductFieldGuess()

    field_name = safe_string(value.get("field_name"))
    header_row_guess = safe_int(value.get("header_row_guess"), default=1)
    confidence = safe_float(value.get("confidence"))
    reason = safe_string(value.get("reason"))

    if header_row_guess < 1:
        header_row_guess = 1

    return ProductFieldGuess(
        field_name=field_name,
        header_row_guess=header_row_guess,
        confidence=confidence,
        reason=reason,
    )


def parse_product_mapping_result(text: str) -> ProductMappingResult:
    """把 LLM 返回的 JSON 文本解析成商品映射结果。"""

    payload = parse_json_object(text)
    if payload is None:
        return ProductMappingResult(raw_text=text, parse_error="LLM 返回内容不是合法 JSON")

    normalization_rules = parse_normalization_rules(payload.get("normalization_rules"))
    mappings = parse_mapping_items(payload.get("mappings"))
    unmatched_a = parse_string_list(payload.get("unmatched_a"))
    unmatched_b = parse_string_list(payload.get("unmatched_b"))
    need_review = parse_review_items(payload.get("need_review"))

    return ProductMappingResult(
        normalization_rules=normalization_rules,
        mappings=mappings,
        unmatched_a=unmatched_a,
        unmatched_b=unmatched_b,
        need_review=need_review,
        raw_text=text,
    )


def build_a_b_intersection(
    a_unique: list[str],
    b_unique: list[str],
    mapping_result: ProductMappingResult | None = None,
) -> dict[str, list[object]]:
    """从 LLM 返回的 mappings 中提取 A/B 一对一匹配、A 未匹配和 B 未使用结果。"""

    matched: list[dict[str, str]] = []
    used_b_values: set[str] = set()
    matched_a_values: set[str] = set()
    a_values = set(a_unique)
    b_values = set(b_unique)

    if mapping_result is not None:
        for item in mapping_result.mappings:
            if item.a_value not in a_values:
                continue
            if item.b_value not in b_values:
                continue
            if item.a_value in matched_a_values or item.b_value in used_b_values:
                continue
            matched.append({"a": item.a_value, "b": item.b_value})
            matched_a_values.add(item.a_value)
            used_b_values.add(item.b_value)

    a_unmatched = [a_value for a_value in a_unique if a_value not in matched_a_values]
    b_unused = [b_value for b_value in b_unique if b_value not in used_b_values]

    return {
        "matched": matched,
        "a_unmatched": a_unmatched,
        "b_unused": b_unused,
    }


def parse_json_object(text: str) -> dict[str, Any] | None:
    """从文本中解析 JSON 对象，兼容 LLM 偶尔返回 Markdown 代码块。"""

    # strip(...)：去掉首尾空白，方便判断开头和结尾。
    stripped = text.strip()
    if not stripped:
        return None

    if stripped.startswith("```"):
        # splitlines(...)：按行拆分，方便去掉 Markdown 代码块的第一行和最后一行。
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        # join(...)：把剩余行重新拼回 JSON 文本。
        stripped = "\n".join(lines).strip()

    try:
        # json.loads(...)：把 JSON 字符串解析成 Python 对象。
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict):
        return payload
    return None


def parse_normalization_rules(value: object) -> dict[str, list[str]]:
    """解析 LLM 返回的规则字段，只保留字符串列表。"""

    result: dict[str, list[str]] = {}
    if not isinstance(value, dict):
        return result

    for key, item in value.items():
        if not isinstance(key, str):
            continue
        result[key] = parse_string_list(item)

    return result


def parse_mapping_items(value: object) -> list[ProductMappingItem]:
    """解析已确认的商品映射列表。"""

    result: list[ProductMappingItem] = []
    if not isinstance(value, list):
        return result

    for item in value:
        if not isinstance(item, dict):
            continue

        standard = safe_string(item.get("standard"))
        a_value = safe_string(item.get("a_value"))
        b_value = safe_string(item.get("b_value"))
        confidence = safe_float(item.get("confidence"))
        reason = safe_string(item.get("reason"))

        if not standard or not a_value or not b_value:
            continue

        mapping_item = ProductMappingItem(
            standard=standard,
            a_value=a_value,
            b_value=b_value,
            confidence=confidence,
            reason=reason,
        )
        result.append(mapping_item)

    return result


def parse_review_items(value: object) -> list[ProductReviewItem]:
    """解析需要人工复核的商品匹配列表。"""

    result: list[ProductReviewItem] = []
    if not isinstance(value, list):
        return result

    for item in value:
        if not isinstance(item, dict):
            continue

        a_value = safe_string(item.get("a_value"))
        b_value = safe_string(item.get("b_value"))
        confidence = safe_float(item.get("confidence"))
        reason = safe_string(item.get("reason"))

        if not a_value and not b_value:
            continue

        review_item = ProductReviewItem(
            a_value=a_value,
            b_value=b_value,
            confidence=confidence,
            reason=reason,
        )
        result.append(review_item)

    return result


def parse_string_list(value: object) -> list[str]:
    """把 LLM 返回的列表安全转换成字符串列表。"""

    result: list[str] = []
    if not isinstance(value, list):
        return result

    for item in value:
        text = safe_string(item)
        if text:
            result.append(text)

    return result


def safe_string(value: object) -> str:
    """把任意值安全转换成去掉首尾空格的字符串。"""

    if value is None:
        return ""
    # str(...)：把数字等内容转为文本；strip(...)：去掉首尾空白。
    return str(value).strip()


def safe_int(value: object, default: int = 0) -> int:
    """把任意值安全转换成整数，失败时返回默认值。"""

    if value is None:
        return default
    try:
        # int(...)：把数字字符串或数字转换为整数。
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: object) -> float:
    """把置信度安全转换成浮点数，失败时返回 0。"""

    if value is None:
        return 0.0
    try:
        # float(...)：把数字字符串或数字转换为小数。
        return float(value)
    except (TypeError, ValueError):
        return 0.0


product_mapping_service = ProductMappingService()
