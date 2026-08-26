from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from agent.domain import LLMConfig, LLMProviderName
from agent.llm_providers import LLMProviderAdapter, LLMResponse, build_llm_adapter
from tools import ExcelSheetPreview


@dataclass
class ReconciliationLLMAgent:
    """财务对账 Agent 的 provider-neutral LLM 编排实体。

    调用方只需要传入模型提供商名称，例如 `anthropic`、`openai`、`deepseek`、
    `qwen` 或 `ollama`，这里会通过 `LLMConfig` 和 `build_llm_adapter` 动态选择
    对应的模型适配器。这个类只负责 LLM 侧的解释和修复建议，不直接读写 Excel。
    """

    # 模型提供商名称，默认使用 Anthropic / Claude。
    provider: LLMProviderName = "anthropic"
    # 可选的模型名；不传时由 provider factory 使用该供应商默认模型。
    model: str | None = None
    # 可选的接口地址；主要用于 OpenAI-compatible provider 或本地 Ollama。
    base_url: str | None = None
    # 可选的 API key 环境变量名；密钥只从环境变量读取，不写死在代码里。
    api_key_env: str | None = None
    # 单次模型请求超时时间。
    timeout_seconds: float = 60.0
    # provider SDK 支持时的最大重试次数。
    max_retries: int = 2
    # 可注入的模型适配器，主要用于测试或上层复用已构造好的 client。
    adapter: LLMProviderAdapter | None = None

    def __post_init__(self) -> None:
        """初始化时根据 provider 配置动态构建模型适配器。"""
        if self.adapter is None:
            config = LLMConfig(
                provider=self.provider,
                model=self.model,
                base_url=self.base_url,
                api_key_env=self.api_key_env,
                timeout_seconds=self.timeout_seconds,
                max_retries=self.max_retries,
            )
            self.adapter = build_llm_adapter(config)
        if self.model is None:
            # 如果调用方没有显式传模型名，则回填 factory 解析出的默认模型名。
            self.model = getattr(self.adapter, "model", None)

    def complete(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        """通过当前 provider adapter 发起一次文本生成请求。"""
        return self.adapter.complete(prompt, max_tokens=max_tokens)

    def analyze_excel_preview(self, preview: ExcelSheetPreview, max_tokens: int = 1024) -> LLMResponse:
        """让 LLM 根据 Excel 预览判断 A 表中有几行数据。"""
        prompt = self.build_excel_preview_prompt(preview)
        return self.complete(prompt, max_tokens=max_tokens)

    def build_excel_preview_prompt(self, preview: ExcelSheetPreview) -> str:
        """把 Excel 预览转换成稳定的 LLM 输入文本。"""
        payload = {
            "sheet_name": preview.sheet_name,
            "max_row": preview.max_row,
            "max_column": preview.max_column,
            "sample_rows": [
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

    def analyze_sheet_structure(
        self,
        a_preview: ExcelSheetPreview,
        b_preview: ExcelSheetPreview,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """让 LLM 分析 A 表和 B 表的结构，并识别商品相关字段。"""

        prompt = self.build_sheet_structure_prompt(a_preview, b_preview)
        return self.complete(prompt, max_tokens=max_tokens)

    def build_sheet_structure_prompt(
        self,
        a_preview: ExcelSheetPreview,
        b_preview: ExcelSheetPreview,
    ) -> str:
        """把 A/B 表结构转换成稳定的 LLM 输入文本。"""

        a_candidate_columns = self.build_column_profiles(a_preview)
        b_candidate_columns = self.build_column_profiles(b_preview)
        b_spec_match_scores = self.build_b_spec_match_scores(a_preview, b_preview)
        payload = {
            "a_sheet": {
                "sheet_name": a_preview.sheet_name,
                "max_row": a_preview.max_row,
                "max_column": a_preview.max_column,
                "candidate_columns": a_candidate_columns,
                "b_spec_match_scores": b_spec_match_scores,
                "sample_rows": [
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
                    for row in a_preview.rows
                ],
            },
            "b_sheet": {
                "sheet_name": b_preview.sheet_name,
                "max_row": b_preview.max_row,
                "max_column": b_preview.max_column,
                "candidate_columns": b_candidate_columns,
                "sample_rows": [
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
                    for row in b_preview.rows
                ],
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

    def build_column_profiles(self, preview: ExcelSheetPreview) -> list[dict[str, object]]:
        """根据预览行提取候选列画像，帮助 LLM 比较字段粒度。"""

        columns = self.collect_preview_columns(preview)
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
        self,
        a_preview: ExcelSheetPreview,
        b_preview: ExcelSheetPreview,
    ) -> dict[str, object]:
        """以 B 表规格列为锚点，计算 A 表候选列的匹配得分。"""

        a_columns = self.collect_preview_columns(a_preview)
        b_columns = self.collect_preview_columns(b_preview)
        b_spec_column = self.find_spec_column(b_columns)

        if b_spec_column is None:
            return {
                "b_spec_found": False,
                "reason": "B 表预览中没有找到表头为规格或包含规格含义的候选列",
                "a_candidates": [],
            }

        b_values = b_spec_column["unique_values"]
        a_candidates = [
            self.score_a_column_against_b_spec(a_column, b_values)
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

    def collect_preview_columns(self, preview: ExcelSheetPreview) -> list[dict[str, object]]:
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

    def find_spec_column(self, columns: list[dict[str, object]]) -> dict[str, object] | None:
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
        self,
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

        normalized_a_values = [self.normalize_match_text(value) for value in a_values]
        normalized_b_values = [self.normalize_match_text(value) for value in b_values]
        normalized_a_set = set(normalized_a_values)

        exact_match_count = sum(1 for value in normalized_b_values if value in normalized_a_set)
        exact_match_ratio = exact_match_count / len(normalized_b_values)

        best_similarities = [
            max(
                self.text_similarity(b_value, a_value)
                for a_value in normalized_a_values
            )
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

    def normalize_match_text(self, value: object) -> str:
        """规整规格文本用于相似度计算，保留中文、字母和数字。"""

        text = str(value).strip().lower()
        return re.sub(r"[\s\-_/|（）()\[\]{}【】]+", "", text)

    def text_similarity(self, left: str, right: str) -> float:
        """返回两个已规整文本的相似度。"""

        if not left or not right:
            return 0.0
        if left == right:
            return 1.0
        return SequenceMatcher(None, left, right).ratio()

    def analyze_product_mapping(
        self,
        a_products: list[str],
        b_products: list[str],
        max_tokens: int = 40960,
    ) -> LLMResponse:
        """让 LLM 分析 A/B 商品规格，并返回商品映射 JSON。"""

        prompt = self.build_product_mapping_prompt(a_products, b_products)
        return self.complete(prompt, max_tokens=max_tokens)

    def build_product_mapping_prompt(self, a_products: list[str], b_products: list[str]) -> str:
        """把去重后的商品列表转换成稳定的 LLM 输入文本。"""

        payload = {
            "a_products": a_products,
            "b_products": b_products,
        }
        # json.dumps(...)：把 Python 字典转成 JSON 字符串；ensure_ascii=False 保留中文。
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
            "8. 每个 B 值最多只能匹配一个 A 值。\n\n"
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

    def explain_plan(self, context: str) -> LLMResponse:
        """让 LLM 用中文解释对账执行计划、关键风险和验收点。"""
        prompt = f"请解释以下对账执行计划，并指出关键风险和验收点：\n{context}"
        return self.complete(prompt)

    def suggest_repairs(self, report: str) -> LLMResponse:
        """根据确定性验收失败报告生成修复建议，不直接修改文件。"""
        prompt = f"请根据以下验收失败报告给出修复建议：\n{report}"
        return self.complete(prompt)


class ClaudeReconciliationAgent(ReconciliationLLMAgent):
    """向后兼容的 Claude 默认 Agent 入口。"""

    def __init__(self, **kwargs: object) -> None:
        # 旧代码如果继续实例化 ClaudeReconciliationAgent，就默认走 Anthropic provider。
        kwargs.setdefault("provider", "anthropic")
        super().__init__(**kwargs)  # type: ignore[arg-type]
