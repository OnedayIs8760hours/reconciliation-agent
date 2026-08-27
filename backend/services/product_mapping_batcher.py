from __future__ import annotations

import json
from typing import Protocol

from agent.llm_providers import LLMResponse
from backend.domain.product_mapping import (
    ProductMappingItem,
    ProductMappingResult,
    ProductReviewItem,
)
from backend.domain.product_mapping_parser import parse_product_mapping_result, safe_string

PRODUCT_MAPPING_BATCH_SIZE = 20


class ProductMappingLLM(Protocol):
    provider: object
    model: object

    def analyze_product_mapping(
        self,
        a_products: list[str],
        b_products: list[str],
    ) -> LLMResponse:
        """返回 A/B 商品映射的 LLM JSON 文本。"""


class ProductMappingBatchAnalyzer:
    """负责商品映射 LLM 分批调用和批次结果合并。"""

    def __init__(self, llm_agent: ProductMappingLLM) -> None:
        self.llm_agent = llm_agent

    def analyze(
        self,
        a_unique: list[str],
        b_unique: list[str],
        *,
        batch_size: int = PRODUCT_MAPPING_BATCH_SIZE,
    ) -> tuple[ProductMappingResult, str, str]:
        """按 A 表商品分批调用 LLM，并把每批 mappings 合并成一个结果。"""

        if batch_size < 1:
            raise ValueError("batch_size 必须大于等于 1")

        all_mappings: list[ProductMappingItem] = []
        all_need_review: list[ProductReviewItem] = []
        used_a_values: set[str] = set()
        used_b_values: set[str] = set()
        raw_batches: list[dict[str, object]] = []
        parse_errors: list[str] = []
        llm_model = safe_string(getattr(self.llm_agent, "model", ""))
        llm_provider = safe_string(getattr(self.llm_agent, "provider", ""))

        for batch_index, a_batch in enumerate(chunk_list(a_unique, batch_size), start=1):
            b_candidates = list(b_unique)
            llm_response = self.llm_agent.analyze_product_mapping(a_batch, b_candidates)
            llm_model = llm_response.model
            llm_provider = llm_response.provider

            batch_result = parse_product_mapping_result(llm_response.text)
            raw_batch: dict[str, object] = {
                "batch_index": batch_index,
                "a_start": (batch_index - 1) * batch_size,
                "a_count": len(a_batch),
                "raw_text": llm_response.text,
            }
            if batch_result.parse_error:
                raw_batch["parse_error"] = batch_result.parse_error
                parse_errors.append(f"第 {batch_index} 批：{batch_result.parse_error}")
            raw_batches.append(raw_batch)

            a_batch_values = set(a_batch)
            b_candidate_values = set(b_candidates)
            for item in batch_result.mappings:
                if item.a_value not in a_batch_values:
                    continue
                if item.b_value not in b_candidate_values:
                    continue
                if item.a_value in used_a_values:
                    continue
                all_mappings.append(item)
                used_a_values.add(item.a_value)
                used_b_values.add(item.b_value)

            for item in batch_result.need_review:
                if item.a_value and item.a_value not in a_batch_values:
                    continue
                if item.b_value and item.b_value not in b_candidate_values:
                    continue
                all_need_review.append(item)

        unmatched_a = [a_value for a_value in a_unique if a_value not in used_a_values]
        unmatched_b = [b_value for b_value in b_unique if b_value not in used_b_values]
        raw_text = json.dumps({"batches": raw_batches}, ensure_ascii=False, indent=2)
        parse_error = "；".join(parse_errors)

        return (
            ProductMappingResult(
                mappings=all_mappings,
                unmatched_a=unmatched_a,
                unmatched_b=unmatched_b,
                need_review=all_need_review,
                raw_text=raw_text,
                parse_error=parse_error,
            ),
            llm_model,
            llm_provider,
        )


def chunk_list(values: list[str], size: int) -> list[list[str]]:
    """按固定大小切分列表。"""

    return [values[index : index + size] for index in range(0, len(values), size)]
