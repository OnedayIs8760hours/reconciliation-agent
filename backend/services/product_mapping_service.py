from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.llm import ReconciliationLLMAgent
from backend.domain.product_mapping import ProductMappingItem, ProductMappingResult, ProductReviewItem
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
        a_column_name: str = "型号",
        b_column_name: str = "规格",
        a_sheet_name: str | None = None,
        b_sheet_name: str | None = None,
        header_row: int = 1,
    ) -> dict[str, object]:
        """从 A/B Excel 中读取商品列，并生成商品映射结果。"""

        # get_unique_column_values(...)：读取指定列，并完成去空、清洗、去重。
        a_unique = excel_tool.get_unique_column_values(
            a_file_path,
            a_column_name,
            sheet_name=a_sheet_name,
            header_row=header_row,
        )
        b_unique = excel_tool.get_unique_column_values(
            b_file_path,
            b_column_name,
            sheet_name=b_sheet_name,
            header_row=header_row,
        )

        # analyze_product_mapping(...)：把去重后的商品列表交给 LLM 做语义匹配。
        llm_response = self.llm_agent.analyze_product_mapping(a_unique, b_unique)
        mapping_result = parse_product_mapping_result(llm_response.text)

        return {
            "a_column_name": a_column_name,
            "b_column_name": b_column_name,
            "a_unique": a_unique,
            "b_unique": b_unique,
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
