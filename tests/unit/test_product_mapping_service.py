from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from agent.llm_providers.base import LLMResponse
from backend.services.product_mapping_service import ProductMappingService


class FakeProductMappingAgent:
    """测试用假 LLM，只返回固定 JSON，避免单元测试调用真实模型。"""

    def analyze_sheet_structure(self, a_preview: object, b_preview: object) -> LLMResponse:
        """模拟 LLM 根据表结构识别商品字段。"""

        text = """
        {
          "a_sheet": {
            "header_row_guess": 2,
            "field_name": "产品名称",
            "confidence": 0.95,
            "reason": "A 表样例中产品名称最像商品字段"
          },
          "b_sheet": {
            "header_row_guess": 1,
            "field_name": "规格",
            "confidence": 0.96,
            "reason": "B 表样例中规格最像商品字段"
          }
        }
        """
        return LLMResponse(text=text, model="fake-model", provider="deepseek")

    def analyze_product_mapping(self, a_products: list[str], b_products: list[str]) -> LLMResponse:
        """模拟 LLM 生成商品映射结果。"""

        text = """
        {
          "normalization_rules": {
            "b_prefix_to_ignore": [],
            "ignorable_separators": []
          },
          "mappings": [
            {
              "standard": "商品A",
              "a_value": "商品A",
              "b_value": "商品A",
              "confidence": 1.0,
              "reason": "名称完全一致"
            }
          ],
          "unmatched_a": ["商品B"],
          "unmatched_b": ["商品C"],
          "need_review": []
        }
        """
        return LLMResponse(text=text, model="fake-model", provider="deepseek")


def create_a_file(file_path: Path) -> None:
    """创建测试 A 表，表头故意放在第 2 行，验证代码不会写死第 1 行。"""

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "A表"
    worksheet.merge_cells("A1:C1")
    worksheet["A1"] = "A 表标题"
    worksheet["A2"] = "日期"
    worksheet["B2"] = "产品名称"
    worksheet["C2"] = "数量"
    worksheet["A3"] = "2026-07-01"
    worksheet["B3"] = " 商品A "
    worksheet["C3"] = 1
    worksheet["A4"] = "2026-07-02"
    worksheet["B4"] = "商品B"
    worksheet["C4"] = 2
    # save(...)：保存为真实 xlsx 文件，测试读取 Excel 的完整流程。
    workbook.save(file_path)


def create_b_file(file_path: Path) -> None:
    """创建测试 B 表，字段名与 A 表不同，验证字段由 LLM 返回。"""

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "B表"
    worksheet["A1"] = "规格"
    worksheet["B1"] = "数量"
    worksheet["A2"] = "商品A"
    worksheet["B2"] = 1
    worksheet["A3"] = "商品C"
    worksheet["B3"] = 3
    workbook.save(file_path)


def test_product_mapping_service_uses_llm_guessed_fields(tmp_path: Path) -> None:
    """商品映射服务应该使用 LLM 识别出的字段，不应该写死 型号/规格 或固定表头行。"""

    a_file_path = tmp_path / "a.xlsx"
    b_file_path = tmp_path / "b.xlsx"
    create_a_file(a_file_path)
    create_b_file(b_file_path)

    service = ProductMappingService(llm_agent=FakeProductMappingAgent())  # type: ignore[arg-type]

    result = service.build_product_mapping(a_file_path, b_file_path)

    assert result["a_column_name"] == "产品名称"
    assert result["b_column_name"] == "规格"
    assert result["a_unique"] == ["商品A", "商品B"]
    assert result["b_unique"] == ["商品A", "商品C"]
    assert result["a_b_intersection"] == ["商品A"]
    assert result["summary"]["mapping_count"] == 1  # type: ignore[index]


def test_product_mapping_service_reports_empty_llm_field(tmp_path: Path) -> None:
    """如果 LLM 没有识别出字段，服务应该给出清晰错误，而不是继续用空字段读取。"""

    class EmptyFieldAgent(FakeProductMappingAgent):
        def analyze_sheet_structure(self, a_preview: object, b_preview: object) -> LLMResponse:
            """模拟 LLM 未识别出 A 表字段。"""

            text = """
            {
              "a_sheet": {"header_row_guess": 1, "field_name": "", "confidence": 0.1, "reason": "看不出"},
              "b_sheet": {"header_row_guess": 1, "field_name": "规格", "confidence": 0.9, "reason": "可识别"}
            }
            """
            return LLMResponse(text=text, model="fake-model", provider="deepseek")

    a_file_path = tmp_path / "a.xlsx"
    b_file_path = tmp_path / "b.xlsx"
    create_a_file(a_file_path)
    create_b_file(b_file_path)

    service = ProductMappingService(llm_agent=EmptyFieldAgent())  # type: ignore[arg-type]

    try:
        service.build_product_mapping(a_file_path, b_file_path)
    except ValueError as exc:
        assert "LLM 没有识别出 A 表商品字段" in str(exc)
    else:
        raise AssertionError("LLM 字段为空时应该抛出 ValueError")


def test_product_mapping_service_matches_identical_values_without_llm_mapping(tmp_path: Path) -> None:
    """完全相同的 A/B 规格应由程序直接关联，不依赖 LLM 是否返回映射。"""

    class EmptyMappingAgent(FakeProductMappingAgent):
        def analyze_product_mapping(self, a_products: list[str], b_products: list[str]) -> LLMResponse:
            text = """
            {
              "normalization_rules": {},
              "mappings": [],
              "unmatched_a": [],
              "unmatched_b": [],
              "need_review": []
            }
            """
            return LLMResponse(text=text, model="fake-model", provider="deepseek")

    a_file_path = tmp_path / "a.xlsx"
    b_file_path = tmp_path / "b.xlsx"
    create_a_file(a_file_path)
    create_b_file(b_file_path)

    service = ProductMappingService(llm_agent=EmptyMappingAgent())  # type: ignore[arg-type]

    result = service.build_product_mapping(a_file_path, b_file_path)

    assert result["a_b_intersection"] == ["商品A"]
