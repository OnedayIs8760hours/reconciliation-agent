from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class ATableRecord:
    """从 A 表明细行读取出的业务记录。"""

    source_row: int
    date_value: date | datetime | str | None
    product_value: str
    quantity: float
    unit_price: float
    amount: float
    document_no: str = ""

    def to_dict(self) -> dict[str, object]:
        """把 A 表记录转成 JSON 字典。"""

        return {
            "source_row": self.source_row,
            "date_value": str(self.date_value) if self.date_value is not None else "",
            "product_value": self.product_value,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "amount": self.amount,
            "document_no": self.document_no,
        }


@dataclass(frozen=True)
class BTableRecord:
    """从 B 表系统出入库明细读取出的标准记录。"""

    source_row: int
    direction: str
    warehouse: str
    system_time: date | datetime | str | None
    document_no: str
    sku: str
    product_name: str
    spec: str
    quantity: float
    unit_price: float
    amount: float
    is_current_month: bool = False
    risk_note: str = ""

    def trace_key(self) -> str:
        """生成 B 表记录追溯键，用来判断是否已经被 C 表承接。"""

        parts = [
            str(self.source_row),
            self.direction,
            self.document_no,
            self.sku,
            self.spec,
            str(self.quantity),
            str(self.unit_price),
            str(self.amount),
        ]
        return "|".join(parts)

    def to_dict(self) -> dict[str, object]:
        """把 B 表记录转成 JSON 字典。"""

        return {
            "source_row": self.source_row,
            "direction": self.direction,
            "warehouse": self.warehouse,
            "system_time": str(self.system_time) if self.system_time is not None else "",
            "document_no": self.document_no,
            "sku": self.sku,
            "product_name": self.product_name,
            "spec": self.spec,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "amount": self.amount,
            "is_current_month": self.is_current_month,
            "risk_note": self.risk_note,
            "trace_key": self.trace_key(),
        }
