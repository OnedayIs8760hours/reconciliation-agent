"""领域模型和工作流导入的冒烟测试。"""

from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from agent.domain.config import LLMConfig, ReconciliationRunConfig
from agent.domain.records import BRecord
from agent.domain.statuses import MatchDirection
from agent.workflows import CTableWorkflow


def test_config_derives_default_output_paths() -> None:
    config = ReconciliationRunConfig(
        a_table_path=Path("a.xlsx"),
        b_table_path=Path("台州b.xlsx"),
        reconciliation_month="2026-07",
        company_profile="default",
    )

    assert config.c_table_path.name == "C表_2026-07_default.xlsx"
    assert config.marked_b_table_path.name == "B表_缺失标注_2026-07_default.xlsx"
    assert config.report_path.name == "核查报告_2026-07_default.md"


def test_b_record_trace_key_uses_directional_values() -> None:
    record = BRecord(
        row_number=2,
        warehouse="主仓",
        document_no="RK001",
        product_code="P001",
        product_name="测试货品",
        spec="规格A",
        inbound_qty=Decimal("2"),
        inbound_unit_price=Decimal("3"),
        inbound_amount=Decimal("6"),
    )

    key = record.trace_key(MatchDirection.INBOUND)

    assert key[-3:] == (Decimal("2"), Decimal("3"), Decimal("6"))


def test_llm_config_defaults_to_anthropic() -> None:
    config = ReconciliationRunConfig(
        a_table_path=Path("a.xlsx"),
        b_table_path=Path("台州b.xlsx"),
        reconciliation_month="2026-07",
    )

    assert config.llm.provider == "anthropic"
    assert config.llm.model is None


def test_llm_config_accepts_custom_provider_and_model() -> None:
    config = LLMConfig(provider="deepseek", model="deepseek-chat")

    assert config.provider == "deepseek"
    assert config.model == "deepseek-chat"


def test_llm_config_rejects_unknown_provider() -> None:
    try:
        LLMConfig(provider="unknown")  # type: ignore[arg-type]
    except ValidationError:
        return

    raise AssertionError("LLMConfig should reject unknown providers")


def test_workflow_imports() -> None:
    assert CTableWorkflow is not None
