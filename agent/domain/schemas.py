"""工作簿架构和列定义。"""

from dataclasses import dataclass
from enum import StrEnum


class WorkbookKind(StrEnum):
    A_TABLE = "A表"
    B_TABLE = "B表"
    C_TABLE = "C表"


@dataclass(frozen=True)
class BTableColumns:
    warehouse: int = 5
    system_time: int = 6
    document_no: int = 7
    product_code: int = 8
    product_name: int = 9
    spec: int = 10
    inbound_qty: int = 11
    inbound_unit_price: int = 12
    inbound_amount: int = 13
    outbound_qty: int = 14
    outbound_unit_price: int = 15
    outbound_amount: int = 16


@dataclass(frozen=True)
class CAppendColumns:
    match_status: str = "匹配状态"
    match_basis: str = "匹配依据"
    b_row_number: str = "B表行号"
    match_direction: str = "匹配方向"
    warehouse: str = "仓库"
    system_time: str = "系统出入库时间"
    document_no: str = "单据编号"
    product_code: str = "货品编号"
    product_name: str = "货品名称"
    spec: str = "规格"
    b_quantity: str = "B数量"
    b_unit_price: str = "B单价"
    b_amount: str = "B金额"
    quantity_diff: str = "差异数量"
    amount_diff: str = "差异金额"
    review_type: str = "复核类型"
    handling_note: str = "处理说明"
