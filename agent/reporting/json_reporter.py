"""JSON 报告输出。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.domain.results import RunReport


class JsonReporter:
    def write(self, report: RunReport, path: Path) -> None:
        path.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")

    def build_payload(
        self,
        *,
        run_id: str,
        status: str,
        c_file: Path,
        report_file: Path,
        verification,
        matching: dict[str, Any],
        coverage: dict[str, int],
        exceptions: list[dict[str, Any]],
        warnings: list[str],
        errors: list[str] | None = None,
        summary: str | None = None,
    ) -> RunReport:
        return RunReport(
            status="passed" if status == "passed" else "failed",
            run_id=run_id,
            c_file=c_file,
            report_file=report_file,
            errors=errors or [],
            warnings=warnings,
            summary=summary,
            verification=verification,
            matching=matching,
            coverage=coverage,
            exceptions=exceptions,
        )
