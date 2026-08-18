"""用于 C 表补充的 A 到 B 匹配引擎。"""

from decimal import Decimal

from rapidfuzz import fuzz

from agent.domain.records import ARecord, BRecord, MatchCandidate
from agent.domain.statuses import MatchDirection, MatchStatus
from agent.rules.default_rules import RuleProfile


class ReconciliationMatcher:
    """将 A 表派生的 C 表行匹配到 B 表入库/出库记录。"""

    def __init__(self, rules: RuleProfile) -> None:
        self.rules = rules

    def match(self, a_records: list[ARecord], b_records: list[BRecord]) -> list[MatchCandidate]:
        """为每个 A 表行返回一个最佳候选项，将多行扩展留给写入器处理。"""
        used_rows: set[int] = set()
        candidates: list[MatchCandidate] = []
        for a_record in a_records:
            candidate = self._match_one(a_record, [b for b in b_records if b.row_number not in used_rows])
            candidates.append(candidate)
            if candidate.status not in {MatchStatus.UNMATCHED, MatchStatus.ZERO_AMOUNT_REVIEW, MatchStatus.REISSUE_REVIEW}:
                used_rows.update(record.row_number for record in candidate.b_records)
        return candidates

    def _match_one(self, a_record: ARecord, b_records: list[BRecord]) -> MatchCandidate:
        direction = self._direction_for(a_record)
        if direction == MatchDirection.ZERO_OR_SPECIAL:
            return self._special_candidate(a_record)

        scored: list[MatchCandidate] = []
        for b_record in b_records:
            quantity = self._b_quantity(b_record, direction)
            amount = self._b_amount(b_record, direction)
            if quantity is None:
                continue
            quantity_diff = self._diff(abs(a_record.quantity or Decimal("0")), quantity)
            amount_diff = self._diff(abs(a_record.amount or Decimal("0")), abs(amount or Decimal("0")))
            if quantity_diff > self.rules.tolerances.quantity:
                continue
            score = self._score(a_record, b_record, amount_diff)
            status = self._status(a_record, b_record, amount_diff)
            scored.append(
                MatchCandidate(
                    a_record=a_record,
                    b_records=[b_record],
                    direction=direction,
                    status=status,
                    basis=self._basis(a_record, b_record, direction),
                    score=score,
                    quantity_diff=quantity_diff,
                    amount_diff=amount_diff,
                    review_type=self._review_type(status),
                )
            )
        if not scored:
            return MatchCandidate(
                a_record=a_record,
                b_records=[],
                direction=direction,
                status=MatchStatus.UNMATCHED,
                basis="未找到数量方向、规格、金额可承接的 B 表记录",
            )
        return sorted(scored, key=lambda candidate: candidate.score, reverse=True)[0]

    def _direction_for(self, a_record: ARecord) -> MatchDirection:
        if a_record.quantity is None or a_record.quantity == 0:
            return MatchDirection.ZERO_OR_SPECIAL
        return MatchDirection.INBOUND if a_record.quantity > 0 else MatchDirection.OUTBOUND

    def _special_candidate(self, a_record: ARecord) -> MatchCandidate:
        remark = (a_record.remark or "") + (a_record.product_name or "")
        status = MatchStatus.REISSUE_REVIEW if "补发" in remark else MatchStatus.ZERO_AMOUNT_REVIEW
        return MatchCandidate(
            a_record=a_record,
            b_records=[],
            direction=MatchDirection.ZERO_OR_SPECIAL,
            status=status,
            basis="零数量/零金额/补发件不自动忽略，进入人工复核队列",
            review_type=status.value,
        )

    def _b_quantity(self, b_record: BRecord, direction: MatchDirection) -> Decimal | None:
        return b_record.inbound_qty if direction == MatchDirection.INBOUND else b_record.outbound_qty

    def _b_amount(self, b_record: BRecord, direction: MatchDirection) -> Decimal | None:
        return b_record.inbound_amount if direction == MatchDirection.INBOUND else b_record.outbound_amount

    def _diff(self, left: Decimal, right: Decimal) -> Decimal:
        return abs(left - right)

    def _score(self, a_record: ARecord, b_record: BRecord, amount_diff: Decimal) -> float:
        spec_score = fuzz.ratio(a_record.normalized_spec or "", b_record.normalized_spec or "") / 100
        name_score = fuzz.partial_ratio(a_record.product_name or "", b_record.product_name or "") / 100
        amount_penalty = float(amount_diff) if amount_diff else 0.0
        return spec_score * 0.45 + name_score * 0.35 + max(0.0, 0.20 - amount_penalty / 1000)

    def _status(self, a_record: ARecord, b_record: BRecord, amount_diff: Decimal) -> MatchStatus:
        spec_equal = (a_record.normalized_spec or "") == (b_record.normalized_spec or "")
        date_equal = a_record.normalized_date == b_record.system_date
        if amount_diff > self.rules.tolerances.amount:
            return MatchStatus.PARTIAL_MATCHED
        if spec_equal and date_equal:
            return MatchStatus.MATCHED_STRICT
        if spec_equal and not date_equal:
            return MatchStatus.MATCHED_DATE_REVIEW
        if not spec_equal and date_equal:
            return MatchStatus.MATCHED_SPEC_REVIEW
        return MatchStatus.MATCHED_DATE_SPEC_REVIEW

    def _basis(self, a_record: ARecord, b_record: BRecord, direction: MatchDirection) -> str:
        return (
            f"{direction.value}匹配：A行{a_record.row_number} -> B行{b_record.row_number}；"
            f"规格={b_record.spec}，单据={b_record.document_no}"
        )

    def _review_type(self, status: MatchStatus) -> str | None:
        return None if status == MatchStatus.MATCHED_STRICT else status.value
