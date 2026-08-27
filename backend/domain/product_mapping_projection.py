from __future__ import annotations

from backend.domain.product_mapping import ProductMappingResult


def build_a_b_intersection(
    a_unique: list[str],
    b_unique: list[str],
    mapping_result: ProductMappingResult | None = None,
) -> dict[str, list[object]]:
    """从 LLM 返回的 mappings 中提取匹配、A 未匹配和 B 未使用结果。"""

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
            if item.a_value in matched_a_values:
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
