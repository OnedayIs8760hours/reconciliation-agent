"""规则加载入口。"""

from typing import Any

from agent.rules.c_table_default import default_rule_config

_FORCED_TRUE = {
    "force_a_c_total_check",
    "force_b_coverage_check",
    "force_formula_error_check",
    "reverse_check_current_month_b",
}


def load_rule_config(overrides: dict[str, Any] | None = None):
    config = default_rule_config()
    overrides = overrides or {}
    for key in _FORCED_TRUE:
        if overrides.get(key) is False:
            raise ValueError(f"强制规则不能关闭：{key}")
    return config.model_copy(update={k: v for k, v in overrides.items() if hasattr(config, k)})
