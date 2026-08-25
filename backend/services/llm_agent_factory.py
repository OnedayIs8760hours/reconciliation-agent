from __future__ import annotations

from agent.llm import ReconciliationLLMAgent
from backend.config import Config


def build_deepseek_agent() -> ReconciliationLLMAgent:
    """创建统一的 DeepSeek LLM Agent，避免各服务重复写模型配置。"""

    # ReconciliationLLMAgent(...)：只传环境变量名，不传真实密钥；真实密钥由 provider 从环境变量读取。
    return ReconciliationLLMAgent(
        provider="deepseek",
        model="deepseek-v4-flash",
        base_url=Config.DEEPSEEK_BASE_URL,
        api_key_env="DEEPSEEK_API_KEY",
    )
