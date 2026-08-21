"""默认 C 表规则。"""

from agent.rules.rule_schema import RuleConfig

DEFAULT_HEADER_ALIASES = {
    "date": ["日期", "业务日期", "出入库日期", "单据日期"],
    "document_no": ["单号", "票据单号", "单据编号", "业务单号"],
    "item_code": ["货品编号", "商品编号", "物料编码", "编码"],
    "item_name": ["产品名称", "货品名称", "商品名称", "品名", "名称"],
    "spec": ["规格", "型号", "规格型号", "颜色规格"],
    "qty": ["数量", "业务数量", "入库数量", "出库数量"],
    "price": ["单价", "成本单价", "入库成本单价", "出库成本单价"],
    "amount": ["金额", "成本金额", "入库成本金额", "出库成本金额"],
    "warehouse": ["仓库"],
    "system_time": ["系统出入库时间", "出入库时间", "系统时间"],
    "in_qty": ["入库数量"],
    "in_price": ["入库成本单价", "入库单价"],
    "in_amount": ["入库成本金额", "入库金额"],
    "out_qty": ["出库数量"],
    "out_price": ["出库成本单价", "出库单价"],
    "out_amount": ["出库成本金额", "出库金额"],
}


def default_rule_config() -> RuleConfig:
    return RuleConfig(header_aliases=DEFAULT_HEADER_ALIASES)
