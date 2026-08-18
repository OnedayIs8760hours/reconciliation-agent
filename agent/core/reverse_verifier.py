"""针对当月 B 表覆盖情况的反向验证。"""

from datetime import date

from agent.domain.records import BRecord, MatchCandidate, MissingBRecord
from agent.domain.statuses import BRecordCoverageStatus, MatchDirection, MatchStatus, MissingType


class ReverseVerifier:
    """确保每条当月 B 表记录均被接受、标记为缺失或排除。"""

    def current_month_records(self, records: list[BRecord], reconciliation_month: str) -> list[BRecord]:
        year, month = [int(part) for part in reconciliation_month.split("-")]
        return [record for record in records if record.system_date and record.system_date.year == year and record.system_date.month == month]

    def coverage_statuses(
        self,
        b_records: list[BRecord],
        candidates: list[MatchCandidate],
        missing_records: list[MissingBRecord],
        manually_excluded_rows: set[int] | None = None,
    ) -> dict[int, BRecordCoverageStatus]:
        manually_excluded_rows = manually_excluded_rows or set()
        accepted = {
            b_record.row_number
            for candidate in candidates
            if candidate.status != MatchStatus.UNMATCHED
            for b_record in candidate.b_records
        }
        missing = {missing.b_record.row_number for missing in missing_records}
        statuses: dict[int, BRecordCoverageStatus] = {}
        for record in b_records:
            if record.row_number in accepted:
                statuses[record.row_number] = BRecordCoverageStatus.ACCEPTED_IN_C
            elif record.row_number in missing:
                statuses[record.row_number] = BRecordCoverageStatus.MARKED_MISSING
            elif record.row_number in manually_excluded_rows:
                statuses[record.row_number] = BRecordCoverageStatus.MANUALLY_EXCLUDED
            else:
                statuses[record.row_number] = BRecordCoverageStatus.UNCOVERED
        return statuses

    def uncovered_rows(self, statuses: dict[int, BRecordCoverageStatus]) -> list[int]:
        return [row for row, status in statuses.items() if status == BRecordCoverageStatus.UNCOVERED]
