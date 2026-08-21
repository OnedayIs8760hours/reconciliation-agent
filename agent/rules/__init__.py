"""规则包。"""

from agent.rules.rule_provider import load_rule_config
from agent.rules.rule_schema import RuleConfig

__all__ = ["RuleConfig", "load_rule_config"]
