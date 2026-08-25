from __future__ import annotations

import json
from dataclasses import dataclass

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

        payload = {
            "a_sheet": {
                "sheet_name": a_preview.sheet_name,
                "max_row": a_preview.max_row,
                "max_column": a_preview.max_column,
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
            "2. 只能返回表头里真实存在的字段名称，字段名要尽量原样返回。\n"
            "3. 如果表里有表头行，请判断 header_row_guess；如果不确定，也要给出最可能的行号。\n"
            "4. A 表通常是型号、产品名称、商品名称、规格名称这类字段；B 表通常是规格、规格值、商品规格这类字段。\n"
            "5. 如果看不出来，就把 confidence 调低，并把 field_name 留空。\n"
            "6. 请只输出 JSON，不要输出 Markdown 代码块，不要输出解释文字。\n\n"
            "JSON 结构必须是：\n"
            "{\n"
            "  \"a_sheet\": {\n"
            "    \"header_row_guess\": 1,\n"
            "    \"field_name\": \"产品名称\",\n"
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

    def analyze_product_mapping(
        self,
        a_products: list[str],
        b_products: list[str],
        max_tokens: int = 4096,
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
            "3. 不要随意忽略数字、型号、颜色、款式、'款'、'新'、'*' 等可能有业务意义的内容。\n"
            "4. 如果不能确定匹配关系，不要强行匹配，应该放入 unmatched 或 need_review。\n"
            "5. 如果双方高度相似但关键属性不同，例如颜色不同，请放入 need_review。\n\n"
            "请只输出 JSON，不要输出 Markdown 代码块，不要输出解释文字。\n"
            "JSON 结构必须是：\n"
            "{\n"
            "  \"normalization_rules\": {\n"
            "    \"b_prefix_to_ignore\": [],\n"
            "    \"ignorable_separators\": []\n"
            "  },\n"
            "  \"mappings\": [\n"
            "    {\n"
            "      \"standard\": \"标准商品规格\",\n"
            "      \"a_value\": \"A表原始商品值\",\n"
            "      \"b_value\": \"B表原始商品值\",\n"
            "      \"confidence\": 1.0,\n"
            "      \"reason\": \"匹配原因\"\n"
            "    }\n"
            "  ],\n"
            "  \"unmatched_a\": [],\n"
            "  \"unmatched_b\": [],\n"
            "  \"need_review\": [\n"
            "    {\n"
            "      \"a_value\": \"A表商品值\",\n"
            "      \"b_value\": \"B表商品值\",\n"
            "      \"confidence\": 0.78,\n"
            "      \"reason\": \"需要复核的原因\"\n"
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
