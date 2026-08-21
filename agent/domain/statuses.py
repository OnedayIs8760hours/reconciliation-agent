"""业务状态枚举。"""

from enum import StrEnum


class TaskStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    GENERATING = "GENERATING"
    MATCHING = "MATCHING"
    VERIFYING = "VERIFYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Direction(StrEnum):
    INBOUND = "入库"
    OUTBOUND = "出库"
    UNKNOWN = "待定"


class MatchStatus(StrEnum):
    MATCHED = "已匹配"
    AMOUNT_REVIEW = "已匹配/金额需复核"
    DATE_REVIEW = "已匹配/日期需复核"
    SPEC_REVIEW = "已匹配/规格需复核"
    DATE_SPEC_REVIEW = "已匹配/日期规格需复核"
    MULTI_MATCHED = "多行匹配"
    UNMATCHED = "未匹配"
    B_APPENDED = "B未匹配/追加"
    ZERO_REVIEW = "零金额需复核"
    ERROR = "异常"
