from __future__ import annotations

from pathlib import Path

from backend.domain.product_mapping import ProductMappingItem, ProductMappingResult
from backend.services.product_mapping_service import ProductMappingLookup
from backend.services.reconciliation_task_service import ReconciliationTaskService


def test_product_mapping_lookup_matches_standard_product() -> None:
    """商品映射查询表应该保留 A 原始值到标准商品再到 B 原始值的链路。"""

    mapping_result = ProductMappingResult(
        mappings=[
            ProductMappingItem(
                standard="标准商品A",
                a_value="A表商品A",
                b_value="B表规格A",
                confidence=0.98,
                reason="测试映射",
            )
        ]
    )

    lookup = ProductMappingLookup(mapping_result)

    assert lookup.get_a_standard("A表商品A") == "标准商品A"
    assert lookup.get_b_standard("B表规格A") == "标准商品A"
    assert lookup.is_match("A表商品A", "B表规格A") is True
    assert lookup.to_dict()["a_to_b_values"] == {"A表商品A": ["B表规格A"]}


def test_reconciliation_task_service_builds_lookup_from_response(tmp_path: Path) -> None:
    """任务编排服务应该能把商品映射响应还原成匹配服务可用的查询表。"""

    service = ReconciliationTaskService(tmp_path)
    product_mapping = {
        "result": {
            "mappings": [
                {
                    "standard": "标准商品A",
                    "a_value": "A表商品A",
                    "b_value": "B表规格A",
                    "confidence": 0.9,
                    "reason": "测试映射",
                }
            ],
            "unmatched_a": [],
            "unmatched_b": [],
            "need_review": [],
        }
    }

    lookup = service.build_product_lookup(product_mapping)

    assert lookup.is_match("A表商品A", "B表规格A") is True
    assert lookup.get_a_standard("未映射A") == "未映射A"
