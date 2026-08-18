"""默认对账规则配置。

公司专用配置可以覆盖容差、列映射、同义词映射和排除规则，
同时保持强制验证契约不变。
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class MatchingTolerance:
    date_days: int = 0
    amount: Decimal = Decimal("0.00")
    quantity: Decimal = Decimal("0")
    fuzzy_spec_threshold: float = 0.88


@dataclass(frozen=True)
class RuleProfile:
    name: str = "default"
    reconciliation_month_header: str = "七月"
    tolerances: MatchingTolerance = field(default_factory=MatchingTolerance)
    spec_suffix_aliases: dict[str, str] = field(
        default_factory=lambda: {
            "站脚款": "站脚",
            "滑轮款": "滑轮",
        }
    )
    removable_spec_tokens: tuple[str, ...] = ("*", " ", "　")
    require_reverse_b_coverage: bool = True
    require_formula_error_free: bool = True
    require_view_reset: bool = True
