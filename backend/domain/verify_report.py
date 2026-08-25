from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VerifyItem:
    """一条强制验收结果。"""

    name: str
    passed: bool
    value: object
    message: str

    def to_dict(self) -> dict[str, object]:
        """把验收项转成 JSON 字典。"""

        return {
            "name": self.name,
            "passed": self.passed,
            "value": self.value,
            "message": self.message,
        }


@dataclass(frozen=True)
class VerifyReport:
    """交付前强制验收报告。"""

    passed: bool
    items: list[VerifyItem] = field(default_factory=list)
    formula_errors: list[str] = field(default_factory=list)
    exceptions: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """把验收报告转成 JSON 字典。"""

        return {
            "passed": self.passed,
            "items": [item.to_dict() for item in self.items],
            "formula_errors": list(self.formula_errors),
            "exceptions": list(self.exceptions),
        }
