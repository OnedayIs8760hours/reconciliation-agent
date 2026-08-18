"""整个对账工作流中使用的状态枚举。"""

from enum import StrEnum


class MatchDirection(StrEnum):
    INBOUND = "入库"
    OUTBOUND = "出库"
    ZERO_OR_SPECIAL = "零金额/特殊"


class MatchStatus(StrEnum):
    PENDING = "待处理"
    MATCHED_STRICT = "已匹配"
    MATCHED_SPEC_REVIEW = "已匹配/规格需复核"
    MATCHED_DATE_REVIEW = "已匹配/日期需复核"
    MATCHED_DATE_SPEC_REVIEW = "已匹配/日期规格需复核"
    PARTIAL_MATCHED = "部分匹配"
    UNMATCHED = "未匹配"
    ZERO_AMOUNT_REVIEW = "零金额需复核"
    REISSUE_REVIEW = "补发件需复核"
    EXCEPTION = "异常"


class BRecordCoverageStatus(StrEnum):
    ACCEPTED_IN_C = "已承接"
    MARKED_MISSING = "已标注缺失"
    MANUALLY_EXCLUDED = "人工排除"
    UNCOVERED = "未覆盖"


class MissingType(StrEnum):
    INBOUND_MISSING = "入库缺失"
    OUTBOUND_MISSING = "出库缺失"
    ZERO_AMOUNT_MISSING = "零金额缺失"
    EMPTY_QUANTITY = "空数量"
