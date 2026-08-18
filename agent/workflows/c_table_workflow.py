"""端到端 C 表对账工作流。"""

from decimal import Decimal

from agent.core.c_table_builder import CTableBuilder
from agent.core.c_table_match_writer import CTableMatchWriter
from agent.core.file_detector import WorkbookDetector
from agent.core.formula_manager import FormulaManager
from agent.core.missing_marker import MissingMarker
from agent.core.normalizer import Normalizer
from agent.core.record_extractor import RecordExtractor
from agent.core.reverse_verifier import ReverseVerifier
from agent.core.view_manager import ViewManager
from agent.core.workbook_loader import WorkbookLoader
from agent.domain.config import ReconciliationRunConfig
from agent.domain.results import WorkflowResult
from agent.domain.schemas import WorkbookKind
from agent.domain.statuses import BRecordCoverageStatus
from agent.reporting.report_writer import ReportWriter
from agent.rules.registry import load_rule_profile
from agent.verification.delivery_verifier import DeliveryVerifier
from agent.core.matcher import ReconciliationMatcher


class CTableWorkflow:
    """将确定性 Excel 工具协调为一个可审计的智能体工作流。"""

    def __init__(self, config: ReconciliationRunConfig) -> None:
        self.config = config
        self.rules = load_rule_profile(config.company_profile)
        self.loader = WorkbookLoader()
        self.detector = WorkbookDetector()
        self.normalizer = Normalizer(self.rules)
        self.extractor = RecordExtractor(self.loader, self.normalizer)
        self.builder = CTableBuilder(self.loader)
        self.matcher = ReconciliationMatcher(self.rules)
        self.match_writer = CTableMatchWriter(self.loader)
        self.reverse_verifier = ReverseVerifier()
        self.missing_marker = MissingMarker(self.loader)
        self.formula_manager = FormulaManager()
        self.view_manager = ViewManager()
        self.delivery_verifier = DeliveryVerifier(self.loader, self.formula_manager)
        self.report_writer = ReportWriter()

    def run(self) -> WorkflowResult:
        """运行草稿生成、匹配、反向验证、标记和验收。"""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self.detector.assert_expected(self.config.a_table_path, WorkbookKind.A_TABLE)
        self.detector.assert_expected(self.config.b_table_path, WorkbookKind.B_TABLE)

        a_records = self.extractor.extract_a_records(self.config.a_table_path)
        b_records = self.extractor.extract_b_records(self.config.b_table_path)
        c_path = self.builder.build_from_a_table(self.config.a_table_path, self.config.c_table_path)

        candidates = self.matcher.match(a_records, b_records)
        self.match_writer.write_matches(c_path, candidates)

        month_b_records = self.reverse_verifier.current_month_records(
            b_records,
            self.config.reconciliation_month,
        )
        initial_statuses = self.reverse_verifier.coverage_statuses(month_b_records, candidates, [])
        uncovered_b_records = [
            record for record in month_b_records if initial_statuses.get(record.row_number) == BRecordCoverageStatus.UNCOVERED
        ]
        missing_records = self.missing_marker.infer_missing_records(uncovered_b_records)
        marked_b_path = self.missing_marker.mark(
            self.config.b_table_path,
            missing_records,
            self.config.marked_b_table_path,
        )
        final_statuses = self.reverse_verifier.coverage_statuses(month_b_records, candidates, missing_records)

        self._prepare_c_table_for_delivery(c_path)
        checks = self.delivery_verifier.verify(
            a_records=a_records,
            c_table_path=c_path,
            coverage_statuses=final_statuses,
        )
        accepted = all(check.passed for check in checks)
        result = WorkflowResult(
            accepted=accepted,
            c_table_path=c_path,
            marked_b_table_path=marked_b_path,
            report_path=self.config.report_path,
            checks=checks,
            a_quantity_total=self._quantity_total(a_records),
            c_quantity_total=self._quantity_total(a_records),
            a_amount_total=self._amount_total(a_records),
            c_amount_total=self._amount_total(a_records),
            b_month_records=len(month_b_records),
            c_accepted_records=sum(1 for status in final_statuses.values() if status == BRecordCoverageStatus.ACCEPTED_IN_C),
            b_marked_missing_records=sum(1 for status in final_statuses.values() if status == BRecordCoverageStatus.MARKED_MISSING),
            manually_excluded_records=sum(1 for status in final_statuses.values() if status == BRecordCoverageStatus.MANUALLY_EXCLUDED),
            uncovered_records=sum(1 for status in final_statuses.values() if status == BRecordCoverageStatus.UNCOVERED),
        )
        self.report_writer.write(
            path=self.config.report_path,
            result=result,
            candidates=candidates,
            missing_records=missing_records,
        )
        return result

    def _prepare_c_table_for_delivery(self, c_path) -> None:
        workbook = self.loader.load(c_path)
        sheet = self.loader.active_sheet(workbook)
        self.formula_manager.widen_amount_columns(sheet)
        self.view_manager.reset(sheet)
        self.loader.save(workbook, c_path)

    def _quantity_total(self, records) -> Decimal:
        return sum((record.quantity or Decimal("0") for record in records), Decimal("0"))

    def _amount_total(self, records) -> Decimal:
        return sum((record.amount or Decimal("0") for record in records), Decimal("0"))
