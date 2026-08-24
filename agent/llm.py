from __future__ import annotations

from dataclasses import dataclass

from agent.domain import LLMConfig, LLMProviderName
from agent.llm_providers import LLMProviderAdapter, LLMResponse, build_llm_adapter


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
