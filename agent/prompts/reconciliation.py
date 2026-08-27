from __future__ import annotations

import json

from agent.domain.excel_profile import build_b_spec_match_scores, build_column_profiles
from tools import ExcelSheetPreview


def build_excel_preview_prompt(preview: ExcelSheetPreview) -> str:
    """把 Excel 预览转换成稳定的 LLM 输入文本。"""

    payload = {
        "sheet_name": preview.sheet_name,
        "max_row": preview.max_row,
        "max_column": preview.max_column,
        "sample_rows": [_preview_row_to_dict(row) for row in preview.rows],
    }
    preview_json = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    return (
        "你是一个 Excel 表结构分析助手。\n"
        "下面是 A 表的工作表名称、实际最大行列数，以及从开头读取的部分样例行。\n"
        "请根据这些信息判断这张 A 表里有几行真正的数据。\n"
        "注意：\n"
        "1. 数据行数不应包含表头行、标题说明行和空行。\n"
        "2. 如果样例不足以准确判断，请结合 max_row 给出最合理判断，并说明原因。\n"
        "3. 请用中文回答，并优先给出明确数字。\n"
        "4. 输出 JSON，字段包括 row_count_guess、header_row_guess、confidence、reason。\n\n"
        f"A 表预览 JSON：\n{preview_json}"
    )


def build_sheet_structure_prompt(
    a_preview: ExcelSheetPreview,
    b_preview: ExcelSheetPreview,
) -> str:
    """把 A/B 表结构转换成稳定的 LLM 输入文本。"""

    payload = {
        "a_sheet": {
            "sheet_name": a_preview.sheet_name,
            "max_row": a_preview.max_row,
            "max_column": a_preview.max_column,
            "candidate_columns": build_column_profiles(a_preview),
            "b_spec_match_scores": build_b_spec_match_scores(a_preview, b_preview),
            "sample_rows": [_preview_row_to_dict(row) for row in a_preview.rows],
        },
        "b_sheet": {
            "sheet_name": b_preview.sheet_name,
            "max_row": b_preview.max_row,
            "max_column": b_preview.max_column,
            "candidate_columns": build_column_profiles(b_preview),
            "sample_rows": [_preview_row_to_dict(row) for row in b_preview.rows],
        },
    }
    structure_json = json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    return (
        "你是一个 Excel 商品字段结构分析助手。\n"
        "现在要先根据 A 表和 B 表的结构，识别每张表里最可能的商品字段。\n\n"
        "重要原则：\n"
        "1. 不要假设字段名固定，必须根据表头和样例判断。\n"
        "2. B表中先查看‘规格’列的值是否存在，然后根据这个值去查看A表中值相似的对应字段。\n"
        "3. A 表字段优先参考 a_sheet.b_spec_match_scores.a_candidates 里的 match_score，得分最高且样例合理的字段优先判定为 A 表商品字段。\n"
        "4. 如果 A 表字段只包含品名，但 B 表规格包含编码、品名、颜色、尺码等更细信息，该 A 字段不能优先于同粒度规格字段。\n"
        "5. 只能返回表头里真实存在的字段名称，字段名要尽量原样返回。\n"
        "6. 如果表里有表头行，请判断 header_row_guess；如果不确定，也要给出最可能的行号。\n"
        "7. B 表如果存在表头名为“规格”的列，优先把 B 表 field_name 返回为“规格”。\n"
        "8. 如果看不出来，就把 confidence 调低，并把 field_name 留空。\n"
        "9. 请只输出 JSON，不要输出 Markdown 代码块，不要输出解释文字。\n\n"
        "JSON 结构必须是：\n"
        "{\n"
        "  \"a_sheet\": {\n"
        "    \"header_row_guess\": 1,\n"
        "    \"field_name\": \"规格\",\n"
        "    \"confidence\": 0.95,\n"
        "    \"reason\": \"为什么认为这是 A 表商品字段\"\n"
        "  },\n"
        "  \"b_sheet\": {\n"
        "    \"header_row_guess\": 1,\n"
        "    \"field_name\": \"规格\",\n"
        "    \"confidence\": 0.95,\n"
        "    \"reason\": \"为什么认为这是 B 表商品字段\"\n"
        "  }\n"
        "}\n\n"
        f"A/B 表结构 JSON：\n{structure_json}"
    )


def build_product_mapping_prompt(a_products: list[str], b_products: list[str]) -> str:
    """把去重后的商品列表转换成稳定的 LLM 输入文本。"""

    payload = {
        "a_products": a_products,
        "b_products": b_products,
    }
    product_json = json.dumps(payload, ensure_ascii=False, indent=2)

    return (
        "你是一个商品规格匹配助手。\n"
        "现在要根据 A 表商品字段和 B 表商品字段，建立商品映射关系。\n\n"
        "重要原则：\n"
        "1. 程序已经完成去空、去重、首尾空格清理和全角半角统一，你不要再重复做去重。\n"
        "2. 你只负责判断商品命名规律、公共商品信息和 A/B 商品对应关系。\n"
        "3. 匹配必须以 A 中每一条数据为基准，依次去 B 中寻找最多一个对应项。\n"
        "4. 匹配分两级：\n"
        "   - 完全匹配：A 和 B 字符串完全一致，直接认为匹配成功。\n"
        "   - 相似匹配：字符串不完全一致时，判断两边是否表达的是同一个商品规格。允许存在非关键描述差异，例如 B 多了 '收纳箱' 这种前缀；但商品型号、款式、尺寸、颜色、结构特征等关键属性不能冲突。\n"
        "5. 不要随意忽略数字、型号、颜色、款式、'款'、'新'、'*' 等可能有业务意义的内容。\n"
        "6. 如果关键属性不同，例如 A 是 '小熊' 而 B 是 '毛衣狗'，即使大部分字符串相同，也不能匹配。\n"
        "7. 如果不能确定匹配关系，不要强行匹配，应该放入 unmatched 或 need_review。\n"
        "8. 每个 A 值最多只能匹配一个 B 值；同一个 B 值可以被多个 A 值重复匹配。\n\n"
        "9. 为了避免输出过长，不要输出 reason 字段，不要解释匹配原因。\n\n"
        "示例：\n"
        "A: WK9648-红箱-毛衣狗-M-鹿角\n"
        "B: WK9648-收纳箱-红箱-毛衣狗-M-鹿角\n"
        "B 多了 '收纳箱'，但核心规格一致，可以匹配。\n\n"
        "A: WK9648-收纳箱-红箱-小熊-M圆角\n"
        "B: WK9648-收纳箱-红箱-毛衣狗-M-圆角\n"
        "'小熊' 和 '毛衣狗' 是关键款式差异，不能匹配。\n\n"
        "请只输出 JSON，不要输出 Markdown 代码块，不要输出解释文字。\n"
        "JSON 结构必须是：\n"
        "{\n"
        "  \"mappings\": [\n"
        "    {\n"
        "      \"a_value\": \"A表原始商品值\",\n"
        "      \"b_value\": \"B表原始商品值\",\n"
        "      \"confidence\": 1.0\n"
        "    }\n"
        "  ],\n"
        "  \"need_review\": [\n"
        "    {\n"
        "      \"a_value\": \"A表商品值\",\n"
        "      \"b_value\": \"B表商品值\",\n"
        "      \"confidence\": 0.78\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"商品列表 JSON：\n{product_json}"
    )


def build_plan_explanation_prompt(context: str) -> str:
    """构造对账执行计划解释 prompt。"""

    return f"请解释以下对账执行计划，并指出关键风险和验收点：\n{context}"


def build_repair_suggestions_prompt(report: str) -> str:
    """构造验收失败修复建议 prompt。"""

    return f"请根据以下验收失败报告给出修复建议：\n{report}"


def _preview_row_to_dict(row: object) -> dict[str, object]:
    return {
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
