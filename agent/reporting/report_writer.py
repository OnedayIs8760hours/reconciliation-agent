"""人类可读的对账报告。"""

from pathlib import Path

from agent.domain.records import MatchCandidate, MissingBRecord
from agent.domain.results import WorkflowResult


class ReportWriter:
    """编写用于审计和交接的 Markdown 报告。"""

    def write(
        self,
        *,
        path: Path,
        result: WorkflowResult,
        candidates: list[MatchCandidate],
        missing_records: list[MissingBRecord],
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.render(result=result, candidates=candidates, missing_records=missing_records),
            encoding="utf-8",
        )
        return path

    def render(
        self,
        *,
        result: WorkflowResult,
        candidates: list[MatchCandidate],
        missing_records: list[MissingBRecord],
    ) -> str:
        lines = [
            "# 财务对账 C 表核查报告",
            "",
            f"交付结论：{'可交付' if result.accepted else '未通过验收'}",
            "",
            "## 输出文件",
            f"- C 表：{result.c_table_path}",
            f"- 标注后 B 表：{result.marked_b_table_path}",
            "",
            "## 强制核查",
        ]
        for check in result.checks:
            lines.append(f"- [{'x' if check.passed else ' '}] {check.name}：{check.summary}")
        lines.extend(
            [
                "",
                "## 匹配状态汇总",
            ]
        )
        status_counts: dict[str, int] = {}
        for candidate in candidates:
            status_counts[candidate.status.value] = status_counts.get(candidate.status.value, 0) + 1
        for status, count in sorted(status_counts.items()):
            lines.append(f"- {status}: {count}")
        lines.extend(["", "## B 表缺失标注", f"- 缺失标注记录数：{len(missing_records)}"])
        for missing in missing_records[:50]:
            lines.append(f"  - B行{missing.b_record.row_number}: {missing.missing_type.value}，{missing.note}")
        if len(missing_records) > 50:
            lines.append(f"  - 其余 {len(missing_records) - 50} 条详见标注后 B 表")
        lines.append("")
        return "\n".join(lines)
