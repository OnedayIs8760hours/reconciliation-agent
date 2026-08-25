from __future__ import annotations

from dataclasses import dataclass, field

from backend.domain.reconciliation_record import BTableRecord


@dataclass(frozen=True)
class MatchResult:
    """一条 A/C 明细和 B 表记录的匹配结果。"""

    a_row: int
    c_row: int
    status: str
    direction: str
    basis: str
    b_records: list[BTableRecord] = field(default_factory=list)
    review_type: str = ""
    suggestion: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        """把匹配结果转成 JSON 字典。"""

        b_rows: list[int] = []
        b_record_dicts: list[dict[str, object]] = []
        for record in self.b_records:
            b_rows.append(record.source_row)
            b_record_dicts.append(record.to_dict())

        return {
            "a_row": self.a_row,
            "c_row": self.c_row,
            "status": self.status,
            "direction": self.direction,
            "basis": self.basis,
            "b_rows": b_rows,
            "b_records": b_record_dicts,
            "review_type": self.review_type,
            "suggestion": self.suggestion,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MatchSummary:
    """C 表正向匹配 B 表后的统计结果。"""

    total_a_records: int = 0
    matched_a_records: int = 0
    matched_b_records: int = 0
    need_review_count: int = 0
    unmatched_count: int = 0
    inserted_rows: int = 0
    results: list[MatchResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """把匹配统计转成 JSON 字典。"""

        return {
            "total_a_records": self.total_a_records,
            "matched_a_records": self.matched_a_records,
            "matched_b_records": self.matched_b_records,
            "need_review_count": self.need_review_count,
            "unmatched_count": self.unmatched_count,
            "inserted_rows": self.inserted_rows,
            "results": [item.to_dict() for item in self.results],
        }
