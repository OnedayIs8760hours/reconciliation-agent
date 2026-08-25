from __future__ import annotations

from dataclasses import dataclass, field

from backend.domain.match_result import MatchSummary
from backend.domain.reconciliation_record import BTableRecord


@dataclass(frozen=True)
class ReverseVerifySummary:
    """B 表本月记录反向核查统计结果。"""

    monthly_records: int = 0
    accepted_by_c: int = 0
    marked_missing: int = 0
    manually_excluded: int = 0
    unexplained: int = 0
    missing_records: list[BTableRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """把反向核查结果转成 JSON 字典。"""

        return {
            "monthly_records": self.monthly_records,
            "accepted_by_c": self.accepted_by_c,
            "marked_missing": self.marked_missing,
            "manually_excluded": self.manually_excluded,
            "unexplained": self.unexplained,
            "missing_records": [record.to_dict() for record in self.missing_records],
        }


class ReverseVerifyService:
    """核查 B 表本月系统记录是否都被 C 表承接或标注。"""

    def verify(
        self,
        b_records: list[BTableRecord],
        match_summary: MatchSummary,
        manual_excluded_keys: set[str] | None = None,
    ) -> ReverseVerifySummary:
        """对 B 表当前月份记录做反向覆盖核查。"""

        if manual_excluded_keys is None:
            manual_excluded_keys = set()

        accepted_keys = self.build_accepted_keys(match_summary)
        monthly_records: list[BTableRecord] = []
        missing_records: list[BTableRecord] = []
        accepted_by_c = 0
        manually_excluded = 0

        for record in b_records:
            if not record.is_current_month:
                continue

            monthly_records.append(record)
            trace_key = record.trace_key()
            if trace_key in accepted_keys:
                accepted_by_c = accepted_by_c + 1
                continue
            if trace_key in manual_excluded_keys:
                manually_excluded = manually_excluded + 1
                continue
            missing_records.append(record)

        return ReverseVerifySummary(
            monthly_records=len(monthly_records),
            accepted_by_c=accepted_by_c,
            marked_missing=len(missing_records),
            manually_excluded=manually_excluded,
            unexplained=0,
            missing_records=missing_records,
        )

    def build_accepted_keys(self, match_summary: MatchSummary) -> set[str]:
        """从 C 表匹配结果中提取已经承接的 B 表追溯键。"""

        accepted_keys: set[str] = set()
        for result in match_summary.results:
            for record in result.b_records:
                # add(...)：把已经写入 C 表的 B 记录追溯键加入集合，方便快速判断是否承接。
                accepted_keys.add(record.trace_key())
        return accepted_keys
