"""匹配引擎。"""

from __future__ import annotations

from decimal import Decimal

from agent.domain.records import ADetailRow, BRecord, MatchResult
from agent.domain.statuses import MatchStatus
from agent.rules.rule_schema import RuleConfig


class Matcher:
    def __init__(self, rule_config: RuleConfig) -> None:
        self.rule_config = rule_config

    def match(self, a_records: list[ADetailRow], b_records: list[BRecord]) -> tuple[list[MatchResult], list[BRecord]]:
        used: set[str] = set()
        results: list[MatchResult] = []
        for a_record in a_records:
            candidates = [record for record in b_records if record.record_id not in used and record.direction == a_record.direction]
            matched = self._strict_match(a_record, candidates) or self._relaxed_match(a_record, candidates)
            if matched:
                used.add(matched.record_id)
                results.append(MatchResult(a_row=a_record.row, status=MatchStatus.MATCHED.value, basis="单行匹配", direction=a_record.direction, trace_records=[matched]))
                continue
            results.append(MatchResult(a_row=a_record.row, status=MatchStatus.UNMATCHED.value, basis="未找到对应 B 表记录", direction=a_record.direction))
        unmatched_b = [record for record in b_records if record.record_id not in used]
        return results, unmatched_b

    def _strict_match(self, a_record: ADetailRow, candidates: list[BRecord]) -> BRecord | None:
        for record in candidates:
            if a_record.item_code and record.item_code and a_record.item_code != record.item_code:
                continue
            if a_record.spec_key and record.spec_key and a_record.spec_key != record.spec_key:
                continue
            if not self._same_abs(a_record.qty, record.qty, Decimal(str(self.rule_config.qty_tolerance))):
                continue
            if not self._same_abs(a_record.amount, record.amount, Decimal(str(self.rule_config.amount_tolerance))):
                continue
            return record
        return None

    def _relaxed_match(self, a_record: ADetailRow, candidates: list[BRecord]) -> BRecord | None:
        for record in candidates:
            name_ok = bool(a_record.item_name and record.item_name and a_record.item_name == record.item_name)
            code_ok = bool(a_record.item_code and record.item_code and a_record.item_code == record.item_code)
            if not (name_ok or code_ok):
                continue
            if self._same_abs(a_record.qty, record.qty, Decimal(str(self.rule_config.qty_tolerance))) and self._same_abs(
                a_record.amount, record.amount, Decimal(str(self.rule_config.amount_tolerance))
            ):
                return record
        return None

    @staticmethod
    def _same_abs(left: Decimal, right: Decimal, tolerance: Decimal) -> bool:
        return abs(abs(left) - abs(right)) <= tolerance
