"""反向覆盖检查。"""

from __future__ import annotations

from agent.domain.records import BRecord, MatchResult


class ReverseChecker:
    def check(self, b_records: list[BRecord], matches: list[MatchResult], appended_b: list[BRecord], manual_excluded: int = 0) -> dict[str, int]:
        covered_ids = [record_id for result in matches for record_id in result.b_record_ids]
        duplicate_count = len(covered_ids) - len(set(covered_ids))
        appended_ids = {record.record_id for record in appended_b}
        covered_set = set(covered_ids)
        all_b_ids = {record.record_id for record in b_records}
        unexplained = all_b_ids - covered_set - appended_ids
        return {
            "b_record_count": len(b_records),
            "covered_b_records": len(covered_set),
            "appended_b_records": len(appended_ids),
            "manual_excluded_b_records": manual_excluded,
            "unexplained_b_records": len(unexplained),
            "duplicate_b_record_count": duplicate_count,
        }
