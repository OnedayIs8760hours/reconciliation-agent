from __future__ import annotations

from backend.domain.json_parser import parse_json_object
from backend.domain.product_mapping import (
    ProductFieldGuess,
    ProductMappingItem,
    ProductMappingResult,
    ProductReviewItem,
)


def parse_field_guess(value: object) -> ProductFieldGuess:
    """解析 LLM 返回的单个表商品字段识别结果。"""

    if not isinstance(value, dict):
        return ProductFieldGuess()

    field_name = safe_string(value.get("field_name"))
    header_row_guess = safe_int(value.get("header_row_guess"), default=1)
    confidence = safe_float(value.get("confidence"))
    reason = safe_string(value.get("reason"))

    header_row_guess = max(header_row_guess, 1)

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

        a_value = safe_string(item.get("a_value"))
        b_value = safe_string(item.get("b_value"))
        confidence = safe_float(item.get("confidence"))
        standard = safe_string(item.get("standard")) or a_value

        if not standard or not a_value or not b_value:
            continue

        result.append(
            ProductMappingItem(
                standard=standard,
                a_value=a_value,
                b_value=b_value,
                confidence=confidence,
            )
        )

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

        if not a_value and not b_value:
            continue

        result.append(
            ProductReviewItem(
                a_value=a_value,
                b_value=b_value,
                confidence=confidence,
            )
        )

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
    return str(value).strip()


def safe_int(value: object, default: int = 0) -> int:
    """把任意值安全转换成整数，失败时返回默认值。"""

    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: object) -> float:
    """把置信度安全转换成浮点数，失败时返回 0。"""

    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
