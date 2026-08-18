"""规则配置注册表。"""

from agent.rules.default_rules import RuleProfile


def load_rule_profile(name: str) -> RuleProfile:
    """加载公司专用规则配置。

    每个配置都保持启用强制 C 表验收检查。
    """
    if name == "default":
        return RuleProfile()
    # 未来的公司专用模块可以在此注册。
    return RuleProfile(name=name)
