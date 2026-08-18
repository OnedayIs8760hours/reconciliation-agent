"""用于编排确定性对账工具的 provider-neutral LLM 客户端。"""

from collections.abc import Iterable

from agent.domain.config import LLMConfig
from agent.llm_providers import LLMProviderAdapter, LLMResponse, build_llm_adapter


class ReconciliationLLMAgent:
    """用于规划、解释和修复建议的轻量 LLM 编排层。

    Excel 修改和验证有意由确定性的 Python 工具处理。LLM 用于编排、
    面向操作人员的解释，以及根据工具结果生成结构化修复建议。
    """

    def __init__(
        self,
        *,
        config: LLMConfig | None = None,
        adapter: LLMProviderAdapter | None = None,
    ) -> None:
        self.config = config or LLMConfig()
        self.adapter = adapter or build_llm_adapter(self.config)

    def explain_plan(self, *, rule_summary: str, available_tools: Iterable[str]) -> LLMResponse:
        """请求 LLM 解释运行计划，而不直接编辑 Excel 文件。"""
        prompt = (
            "你是财务对账 C 表 Agent 的编排层。请用简洁中文说明本次运行计划。\n"
            "必须强调：Excel 读写、匹配、反向核查、验收由确定性工具完成；"
            "LLM 只负责编排解释和异常处置建议。\n\n"
            f"规则摘要：{rule_summary}\n"
            f"可用工具：{', '.join(available_tools)}"
        )
        return self.adapter.complete(prompt, max_tokens=1200)

    def suggest_repairs(self, verification_report: str) -> LLMResponse:
        """根据失败的确定性检查生成面向操作人员的修复指引。"""
        prompt = (
            "以下是确定性验收工具输出的失败报告。请给出修复顺序和人工复核建议，"
            "不要声称已经修改文件。\n\n"
            f"{verification_report}"
        )
        return self.adapter.complete(prompt, max_tokens=2000)


class ClaudeReconciliationAgent(ReconciliationLLMAgent):
    """向后兼容的 Claude 默认 LLM Agent 名称。"""

    def __init__(
        self,
        *,
        model: str = "claude-opus-5",
        config: LLMConfig | None = None,
        adapter: LLMProviderAdapter | None = None,
        client=None,
    ) -> None:
        if adapter is None and client is not None:
            from agent.llm_providers import AnthropicAdapter

            adapter = AnthropicAdapter(model=model, client=client)
        super().__init__(config=config or LLMConfig(provider="anthropic", model=model), adapter=adapter)
