"""A、B、C 表和匹配结果的核心领域记录。"""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agent.domain.statuses import MatchDirection, MatchStatus, MissingType


class WorkbookIdentity(BaseModel):
    """带有验证元数据的已识别工作簿。"""

    path: Path
    kind: str
    sheet_name: str | None = None
    confidence: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class ARecord(BaseModel):
    """一条继承自 A 表的原始业务行。"""

    row_number: int
    display_date: str | None = None
    normalized_date: date | None = None
    document_no: str | None = None
    product_name: str | None = None
    normalized_spec: str | None = None
    unit: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    remark: str | None = None
    raw_values: dict[str, Any] = Field(default_factory=dict)


class BRecord(BaseModel):
    """一条来自 B 表的系统入库/出库行。"""

    row_number: int
    warehouse: str | None = None
    system_time: datetime | None = None
    system_date: date | None = None
    document_no: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    spec: str | None = None
    normalized_spec: str | None = None
    inbound_qty: Decimal | None = None
    inbound_unit_price: Decimal | None = None
    inbound_amount: Decimal | None = None
    outbound_qty: Decimal | None = None
    outbound_unit_price: Decimal | None = None
    outbound_amount: Decimal | None = None

    def trace_key(self, direction: MatchDirection) -> tuple[Any, ...]:
        """为入库或出库追踪构建反向验证键。"""
        if direction == MatchDirection.INBOUND:
            quantity = self.inbound_qty
            unit_price = self.inbound_unit_price
            amount = self.inbound_amount
        else:
            quantity = self.outbound_qty
            unit_price = self.outbound_unit_price
            amount = self.outbound_amount
        return (
            self.warehouse,
            self.system_time,
            self.document_no,
            self.product_code,
            self.product_name,
            self.spec,
            quantity,
            unit_price,
            amount,
        )


class MatchCandidate(BaseModel):
    """一条 C 表行与一条或多条 B 表行之间的潜在映射。"""

    a_record: ARecord
    b_records: list[BRecord]
    direction: MatchDirection
    status: MatchStatus
    basis: str
    score: float = 0.0
    quantity_diff: Decimal = Decimal("0")
    amount_diff: Decimal | None = None
    review_type: str | None = None


class MissingBRecord(BaseModel):
    """因未带入 C 表而必须标记的 B 表行。"""

    b_record: BRecord
    direction: MatchDirection
    missing_type: MissingType
    basis: str
    note: str
    manual_row_number: int | None = None
