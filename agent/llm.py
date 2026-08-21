"""DeepSeek 智能摘要门面。"""

from __future__ import annotations

import json
from typing import Any

from agent.domain.config import LLMConfig
from agent.llm_providers.base import LLMMessage
from agent.llm_providers.factory import build_llm_provider


class LLMService:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()

    def summarize_report(self, report_payload: dict[str, Any]) -> tuple[str | None, str | None]:
        """用 DeepSeek 总结报告；失败时返回 warning，不影响对账验收。"""
        try:
            provider = build_llm_provider(self.config)
            payload = json.dumps(report_payload, ensure_ascii=False, default=str)[:12000]
            response = provider.complete(
                [
                    LLMMessage(
                        role="system",
                        content=(
                            "你是财务对账 C 表制作助手。只能基于输入的结构化报告进行总结，"
                            "不得改写验收结果，不得声称未通过的核查已通过。"
                        ),
                    ),
                    LLMMessage(
                        role="user",
                        content=(
                            "请用中文输出一段简洁的对账摘要，包含总体结论、关键差异、"
                            f"需人工复核事项。报告 JSON：{payload}"
                        ),
                    ),
                ]
            )
            return response.content.strip() or None, None
        except Exception as exc:  # noqa: BLE001 - LLM 失败必须降级为 warning
            return None, f"智能摘要不可用：{exc}"
