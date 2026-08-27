from __future__ import annotations

from dataclasses import dataclass

from agent.domain import LLMConfig, LLMProviderName
from agent.domain.excel_profile import (
    build_b_spec_match_scores,
    build_column_profiles,
    collect_preview_columns,
    find_spec_column,
    normalize_match_text,
    score_a_column_against_b_spec,
    text_similarity,
)
from agent.llm_providers import LLMProviderAdapter, LLMResponse, build_llm_adapter
from agent.prompts import (
    build_excel_preview_prompt,
    build_plan_explanation_prompt,
    build_product_mapping_prompt,
    build_repair_suggestions_prompt,
    build_sheet_structure_prompt,
)
from tools import ExcelSheetPreview


@dataclass
class ReconciliationLLMAgent:
    """财务对账 Agent 的 provider-neutral LLM 编排实体。

    这个类只负责 provider adapter 的生命周期和调用入口。具体 prompt 构造、
    Excel 预览画像和匹配打分逻辑放在独立模块中，避免 LLM 客户端类承载业务细节。
    """

    provider: LLMProviderName = "anthropic"
    model: str | None = None
    base_url: str | None = None
    api_key_env: str | None = None
    timeout_seconds: float = 60.0
    max_retries: int = 2
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
            self.model = getattr(self.adapter, "model", None)

    def complete(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        """通过当前 provider adapter 发起一次文本生成请求。"""

        return self.adapter.complete(prompt, max_tokens=max_tokens)

    def analyze_excel_preview(
        self,
        preview: ExcelSheetPreview,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """让 LLM 根据 Excel 预览判断 A 表中有几行数据。"""

        return self.complete(self.build_excel_preview_prompt(preview), max_tokens=max_tokens)

    def build_excel_preview_prompt(self, preview: ExcelSheetPreview) -> str:
        """兼容旧调用路径，实际实现位于 agent.prompts。"""

        return build_excel_preview_prompt(preview)

    def analyze_sheet_structure(
        self,
        a_preview: ExcelSheetPreview,
        b_preview: ExcelSheetPreview,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """让 LLM 分析 A 表和 B 表的结构，并识别商品相关字段。"""

        return self.complete(
            self.build_sheet_structure_prompt(a_preview, b_preview),
            max_tokens=max_tokens,
        )

    def build_sheet_structure_prompt(
        self,
        a_preview: ExcelSheetPreview,
        b_preview: ExcelSheetPreview,
    ) -> str:
        """兼容旧调用路径，实际实现位于 agent.prompts。"""

        return build_sheet_structure_prompt(a_preview, b_preview)

    def build_column_profiles(self, preview: ExcelSheetPreview) -> list[dict[str, object]]:
        """兼容旧调用路径，实际实现位于 agent.domain.excel_profile。"""

        return build_column_profiles(preview)

    def build_b_spec_match_scores(
        self,
        a_preview: ExcelSheetPreview,
        b_preview: ExcelSheetPreview,
    ) -> dict[str, object]:
        """兼容旧调用路径，实际实现位于 agent.domain.excel_profile。"""

        return build_b_spec_match_scores(a_preview, b_preview)

    def collect_preview_columns(self, preview: ExcelSheetPreview) -> list[dict[str, object]]:
        """兼容旧调用路径，实际实现位于 agent.domain.excel_profile。"""

        return collect_preview_columns(preview)

    def find_spec_column(self, columns: list[dict[str, object]]) -> dict[str, object] | None:
        """兼容旧调用路径，实际实现位于 agent.domain.excel_profile。"""

        return find_spec_column(columns)

    def score_a_column_against_b_spec(
        self,
        a_column: dict[str, object],
        b_values: list[str],
    ) -> dict[str, object]:
        """兼容旧调用路径，实际实现位于 agent.domain.excel_profile。"""

        return score_a_column_against_b_spec(a_column, b_values)

    def normalize_match_text(self, value: object) -> str:
        """兼容旧调用路径，实际实现位于 agent.domain.excel_profile。"""

        return normalize_match_text(value)

    def text_similarity(self, left: str, right: str) -> float:
        """兼容旧调用路径，实际实现位于 agent.domain.excel_profile。"""

        return text_similarity(left, right)

    def analyze_product_mapping(
        self,
        a_products: list[str],
        b_products: list[str],
        max_tokens: int = 40960,
    ) -> LLMResponse:
        """让 LLM 分析 A/B 商品规格，并返回商品映射 JSON。"""

        return self.complete(
            self.build_product_mapping_prompt(a_products, b_products),
            max_tokens=max_tokens,
        )

    def build_product_mapping_prompt(self, a_products: list[str], b_products: list[str]) -> str:
        """兼容旧调用路径，实际实现位于 agent.prompts。"""

        return build_product_mapping_prompt(a_products, b_products)

    def explain_plan(self, context: str) -> LLMResponse:
        """让 LLM 用中文解释对账执行计划、关键风险和验收点。"""

        return self.complete(build_plan_explanation_prompt(context))

    def suggest_repairs(self, report: str) -> LLMResponse:
        """根据确定性验收失败报告生成修复建议，不直接修改文件。"""

        return self.complete(build_repair_suggestions_prompt(report))


class ClaudeReconciliationAgent(ReconciliationLLMAgent):
    """向后兼容的 Claude 默认 Agent 入口。"""

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("provider", "anthropic")
        super().__init__(**kwargs)  # type: ignore[arg-type]
