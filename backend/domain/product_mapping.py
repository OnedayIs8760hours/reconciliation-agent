from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProductFieldGuess:
    """LLM 识别出来的商品字段信息。"""

    field_name: str = ""
    header_row_guess: int = 1
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        """把字段识别结果转成可以直接写入 JSON 的字典。"""

        return {
            "field_name": self.field_name,
            "header_row_guess": self.header_row_guess,
            "confidence": self.confidence,
            "reason": self.reason,
        }


# frozen 的作用是让 dataclass 实例不可变，防止属性被修改，提高数据安全性。
@dataclass(frozen=True)
class ProductStructureResult:
    """A/B 表商品字段结构识别结果。"""

    a_sheet: ProductFieldGuess = field(default_factory=ProductFieldGuess)
    b_sheet: ProductFieldGuess = field(default_factory=ProductFieldGuess)
    raw_text: str = ""
    parse_error: str = ""

    def to_dict(self) -> dict[str, object]:
        """把结构识别结果转成可以直接写入 JSON 的字典。"""

        payload: dict[str, object] = {
            "a_sheet": self.a_sheet.to_dict(),
            "b_sheet": self.b_sheet.to_dict(),
        }

        if self.raw_text:
            payload["raw_text"] = self.raw_text
        if self.parse_error:
            payload["parse_error"] = self.parse_error

        return payload


@dataclass(frozen=True)
class ProductMappingItem:
    """商品标准映射项。"""

    standard: str
    a_value: str
    b_value: str
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        """把映射项转成可以直接写入 JSON 的字典。"""

        return {
            "standard": self.standard,
            "a_value": self.a_value,
            "b_value": self.b_value,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ProductReviewItem:
    """需要人工复核的商品匹配项。"""

    a_value: str
    b_value: str
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        """把待复核项转成可以直接写入 JSON 的字典。"""

        return {
            "a_value": self.a_value,
            "b_value": self.b_value,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ProductMappingResult:
    """商品规格去重与公共信息提取结果。"""

    normalization_rules: dict[str, list[str]] = field(default_factory=dict)
    mappings: list[ProductMappingItem] = field(default_factory=list)
    unmatched_a: list[str] = field(default_factory=list)
    unmatched_b: list[str] = field(default_factory=list)
    need_review: list[ProductReviewItem] = field(default_factory=list)
    raw_text: str = ""
    parse_error: str = ""

    def to_dict(self) -> dict[str, object]:
        """把整个结果转成 JSON 友好的字典结构。"""

        mappings: list[dict[str, object]] = []
        for item in self.mappings:
            mappings.append(item.to_dict())

        need_review: list[dict[str, object]] = []
        for item in self.need_review:
            need_review.append(item.to_dict())

        payload: dict[str, object] = {
            "normalization_rules": self.normalization_rules,
            "mappings": mappings,
            "unmatched_a": list(self.unmatched_a),
            "unmatched_b": list(self.unmatched_b),
            "need_review": need_review,
        }

        if self.raw_text:
            payload["raw_text"] = self.raw_text
        if self.parse_error:
            payload["parse_error"] = self.parse_error

        return payload

    @property
    def mapping_count(self) -> int:
        """返回成功建立的映射数量。"""

        return len(self.mappings)

    @property
    def review_count(self) -> int:
        """返回需要人工复核的数量。"""

        return len(self.need_review)
