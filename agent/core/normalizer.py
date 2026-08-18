"""用于对账匹配的值规范化工具。"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from dateutil import parser

from agent.rules.default_rules import RuleProfile


class Normalizer:
    """在不修改源数据的情况下规范化日期、数字、产品名称和规格。"""

    def __init__(self, rules: RuleProfile) -> None:
        self.rules = rules

    def date_value(self, value: Any) -> date | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return parser.parse(str(value)).date()
        except (ValueError, TypeError, OverflowError):
            return None

    def datetime_value(self, value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        try:
            return parser.parse(str(value))
        except (ValueError, TypeError, OverflowError):
            return None

    def decimal_value(self, value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value).replace(",", "").strip())
        except (InvalidOperation, AttributeError):
            return None

    def text_value(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value).strip()

    def spec_value(self, value: Any) -> str | None:
        text = self.text_value(value)
        if not text:
            return None
        for token in self.rules.removable_spec_tokens:
            text = text.replace(token, "")
        for source, target in self.rules.spec_suffix_aliases.items():
            text = text.replace(source, target)
        return text.strip() or None
