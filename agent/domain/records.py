"""对账领域记录。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from agent.domain.statuses import Direction


@dataclass(slots=True)
class ADetailRow:
    row: int
    date_key: str | None
    document_no: str | None
    item_code: str | None
    item_name: str | None
    spec_raw: str | None
    spec_key: str | None
    qty: Decimal
    price: Decimal | None
    amount: Decimal
    direction: Direction
    raw_values: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BRecord:
    record_id: str
    row: int
    direction: Direction
    warehouse: str | None
    system_time: datetime | str | None
    date_key: str | None
    document_no: str | None
    item_code: str | None
    item_name: str | None
    spec_raw: str | None
    spec_key: str | None
    qty: Decimal
    price: Decimal | None
    amount: Decimal
    raw_fields: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MatchResult:
    a_row: int
    status: str
    basis: str
    direction: Direction
    trace_records: list[BRecord] = field(default_factory=list)
    diff_qty: Decimal | None = None
    diff_amount: Decimal | None = None

    @property
    def b_record_ids(self) -> list[str]:
        return [record.record_id for record in self.trace_records]


@dataclass(slots=True)
class ExceptionRecord:
    id: str
    row: int
    systemTime: str
    documentNo: str
    sku: str
    productName: str
    spec: str
    quantity: float
    unitCost: float
    amount: float
    type: str
    reason: str
