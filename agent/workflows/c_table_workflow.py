"""C 表制作工作流。"""

from __future__ import annotations

from dotenv import load_dotenv

from agent.core.a_parser import AParser
from agent.core.b_parser import BParser
from agent.core.c_table_writer import CTableWriter
from agent.core.c_workbook_builder import CWorkbookBuilder
from agent.core.formula_manager import FormulaManager
from agent.core.input_resolver import InputResolver
from agent.core.matcher import Matcher
from agent.core.missing_resolver import MissingResolver
from agent.core.reverse_checker import ReverseChecker
from agent.core.view_manager import ViewManager
from agent.core.workbook_loader import load_excel_workbook
from agent.core.workbook_profiler import WorkbookProfiler
from agent.domain.config import ReconciliationRunRequest
from agent.domain.results import RunReport, VerificationReport
from agent.llm import LLMService
from agent.reporting.json_reporter import JsonReporter
from agent.rules.rule_provider import load_rule_config
from agent.verification.verifier import Verifier


class CTableWorkflow:
    def run(self, request: ReconciliationRunRequest) -> RunReport:
        load_dotenv()
        context = InputResolver().resolve(request)
        reporter = JsonReporter()
        warnings: list[str] = []
        try:
            rule_config = load_rule_config(request.user_overrides)
            profiler = WorkbookProfiler(rule_config)

            a_workbook = load_excel_workbook(context.a_path, data_only=False)
            b_workbook = load_excel_workbook(context.b_path, data_only=False)
            a_sheet = a_workbook.active
            b_sheet = b_workbook.active
            a_profile = profiler.profile(a_sheet)
            b_profile = profiler.profile(b_sheet)

            c_workbook, c_sheet = CWorkbookBuilder().build_from_a(context.a_path, context.c_path)
            a_records = AParser().parse(a_sheet, a_profile)
            b_records = BParser().parse(b_sheet, b_profile, context.month)
            matches, unmatched_b = Matcher(rule_config).match(a_records, b_records)
            appended_b = MissingResolver().resolve(unmatched_b)

            writer = CTableWriter()
            trace_columns = writer.write_matches(c_sheet, a_profile.header_row, matches)
            appended_count = writer.append_unmatched_b(c_sheet, trace_columns, appended_b)
            ViewManager().reset(c_sheet, a_profile.header_row)
            formula_inspection = FormulaManager().inspect(c_sheet)
            c_workbook.save(context.c_path)

            coverage = ReverseChecker().check(b_records, matches, appended_b)
            verification = Verifier(rule_config).verify(a_records=a_records, coverage=coverage, formula_inspection=formula_inspection)
            matching = {
                "a_record_count": len(a_records),
                "matched_a_rows": sum(1 for result in matches if result.trace_records),
                "unmatched_a_rows": sum(1 for result in matches if not result.trace_records),
                "unmatched_b_appended": appended_count,
            }
            exceptions = [
                {
                    "id": f"A{result.a_row}",
                    "row": result.a_row,
                    "type": result.status,
                    "reason": result.basis,
                    "documentNo": "",
                    "sku": "",
                    "productName": "",
                    "spec": "",
                    "quantity": 0,
                    "unitCost": 0,
                    "amount": 0,
                    "systemTime": "",
                }
                for result in matches
                if not result.trace_records
            ]
            status = "passed" if verification.passed else "failed"
            preview_payload = {
                "status": status,
                "matching": matching,
                "coverage": coverage,
                "verification": verification.model_dump(mode="json"),
                "exceptions": exceptions[:20],
            }
            summary, llm_warning = LLMService(request.llm).summarize_report(preview_payload)
            if llm_warning:
                warnings.append(llm_warning)
            report = reporter.build_payload(
                run_id=context.run_id,
                status=status,
                c_file=context.c_path,
                report_file=context.report_path,
                verification=verification,
                matching=matching,
                coverage=coverage,
                exceptions=exceptions,
                warnings=warnings,
                summary=summary,
            )
            reporter.write(report, context.report_path)
            return report
        except Exception as exc:  # noqa: BLE001 - 工作流需要生成失败报告
            verification = VerificationReport(passed=False, checks=[{"name": "工作流执行", "passed": False, "error": str(exc)}])
            report = RunReport(
                status="failed",
                run_id=context.run_id,
                c_file=context.c_path if context.c_path.exists() else None,
                report_file=context.report_path,
                errors=[str(exc)],
                warnings=warnings,
                verification=verification,
            )
            reporter.write(report, context.report_path)
            return report
