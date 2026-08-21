"""未匹配 B 表处理。"""

from __future__ import annotations

from agent.domain.records import BRecord


class MissingResolver:
    def resolve(self, unmatched_b: list[BRecord]) -> list[BRecord]:
        return unmatched_b
