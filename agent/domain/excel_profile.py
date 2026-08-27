from __future__ import annotations

import re
from difflib import SequenceMatcher

from tools import ExcelSheetPreview


def build_column_profiles(preview: ExcelSheetPreview) -> list[dict[str, object]]:
    """根据预览行提取候选列画像，帮助 LLM 比较字段粒度。"""

    columns = collect_preview_columns(preview)
    profiles: list[dict[str, object]] = []

    for column in columns:
        unique_values = column["unique_values"]
        if not unique_values:
            continue
        profiles.append(
            {
                "assumed_header_row": column["assumed_header_row"],
                "column": column["column"],
                "header": column["header"],
                "non_empty_sample_count": column["non_empty_sample_count"],
                "unique_sample_count": len(unique_values),
                "sample_values": unique_values[:8],
            }
        )

    return profiles


def build_b_spec_match_scores(
    a_preview: ExcelSheetPreview,
    b_preview: ExcelSheetPreview,
) -> dict[str, object]:
    """以 B 表规格列为锚点，计算 A 表候选列的匹配得分。"""

    a_columns = collect_preview_columns(a_preview)
    b_columns = collect_preview_columns(b_preview)
    b_spec_column = find_spec_column(b_columns)

    if b_spec_column is None:
        return {
            "b_spec_found": False,
            "reason": "B 表预览中没有找到表头为规格或包含规格含义的候选列",
            "a_candidates": [],
        }

    b_values = b_spec_column["unique_values"]
    a_candidates = [
        score_a_column_against_b_spec(a_column, b_values)
        for a_column in a_columns
        if a_column["unique_values"]
    ]
    a_candidates.sort(key=lambda candidate: candidate["match_score"], reverse=True)

    return {
        "b_spec_found": True,
        "b_spec_column": {
            "assumed_header_row": b_spec_column["assumed_header_row"],
            "column": b_spec_column["column"],
            "header": b_spec_column["header"],
            "unique_sample_count": len(b_values),
            "sample_values": b_values[:8],
        },
        "a_candidates": a_candidates,
    }


def collect_preview_columns(preview: ExcelSheetPreview) -> list[dict[str, object]]:
    """按预览里最可能的表头行收集每列样例值。"""

    if not preview.rows:
        return []

    header_row_index, header_row = next(
        (
            (index, row)
            for index, row in enumerate(preview.rows)
            if sum(1 for cell in row.cells if cell.display_text.strip()) > 1
        ),
        (0, preview.rows[0]),
    )
    header_by_column = {
        cell.column: cell.display_text.strip()
        for cell in header_row.cells
        if cell.display_text.strip()
    }
    values_by_column: dict[int, list[str]] = {column: [] for column in header_by_column}

    for row in preview.rows[header_row_index + 1 :]:
        for cell in row.cells:
            if cell.column not in values_by_column:
                continue
            value = cell.display_text.strip()
            if value:
                values_by_column[cell.column].append(value)

    columns: list[dict[str, object]] = []
    for column, header in header_by_column.items():
        values = values_by_column[column]
        columns.append(
            {
                "assumed_header_row": header_row.row_number,
                "column": column,
                "header": header,
                "non_empty_sample_count": len(values),
                "unique_values": list(dict.fromkeys(values)),
            }
        )

    return columns


def find_spec_column(columns: list[dict[str, object]]) -> dict[str, object] | None:
    """优先找 B 表表头名为规格的列，找不到再找包含规格语义的列。"""

    for column in columns:
        if column["header"] == "规格":
            return column

    for column in columns:
        header = str(column["header"])
        if "规格" in header:
            return column

    return None


def score_a_column_against_b_spec(
    a_column: dict[str, object],
    b_values: list[str],
) -> dict[str, object]:
    """计算 A 表候选列与 B 表规格列样例值的匹配分数。"""

    a_values = a_column["unique_values"]
    if not isinstance(a_values, list) or not a_values or not b_values:
        return {
            "column": a_column["column"],
            "header": a_column["header"],
            "match_score": 0,
            "sample_values": [],
        }

    normalized_a_values = [normalize_match_text(value) for value in a_values]
    normalized_b_values = [normalize_match_text(value) for value in b_values]
    normalized_a_set = set(normalized_a_values)

    exact_match_count = sum(1 for value in normalized_b_values if value in normalized_a_set)
    exact_match_ratio = exact_match_count / len(normalized_b_values)

    best_similarities = [
        max(text_similarity(b_value, a_value) for a_value in normalized_a_values)
        for b_value in normalized_b_values
    ]
    average_best_similarity = sum(best_similarities) / len(best_similarities)

    unique_count_ratio = min(len(a_values), len(b_values)) / max(len(a_values), len(b_values))
    average_a_length = sum(len(value) for value in normalized_a_values) / len(normalized_a_values)
    average_b_length = sum(len(value) for value in normalized_b_values) / len(normalized_b_values)
    granularity_ratio = min(average_a_length / average_b_length, 1.0) if average_b_length else 0.0

    match_score = round(
        100
        * (
            0.45 * average_best_similarity
            + 0.25 * exact_match_ratio
            + 0.15 * unique_count_ratio
            + 0.15 * granularity_ratio
        ),
        2,
    )

    return {
        "assumed_header_row": a_column["assumed_header_row"],
        "column": a_column["column"],
        "header": a_column["header"],
        "match_score": match_score,
        "average_best_similarity": round(average_best_similarity, 4),
        "exact_match_ratio": round(exact_match_ratio, 4),
        "unique_count_ratio": round(unique_count_ratio, 4),
        "granularity_ratio": round(granularity_ratio, 4),
        "sample_values": a_values[:8],
    }


def normalize_match_text(value: object) -> str:
    """规整规格文本用于相似度计算，保留中文、字母和数字。"""

    text = str(value).strip().lower()
    return re.sub(r"[\s\-_/|（）()\[\]{}【】]+", "", text)


def text_similarity(left: str, right: str) -> float:
    """返回两个已规整文本的相似度。"""

    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    return SequenceMatcher(None, left, right).ratio()
