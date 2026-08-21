"""输入解析与输出路径生成。"""

from __future__ import annotations

import uuid
from pathlib import Path

from agent.domain.config import ReconciliationRunRequest, RunContext


class InputResolver:
    def resolve(self, request: ReconciliationRunRequest) -> RunContext:
        a_path = request.a_file.resolve()
        b_path = request.b_file.resolve()
        if not a_path.exists():
            raise FileNotFoundError(f"A 表不存在：{a_path}")
        if not b_path.exists():
            raise FileNotFoundError(f"B 表不存在：{b_path}")
        if a_path.suffix.lower() != ".xlsx" or b_path.suffix.lower() != ".xlsx":
            raise ValueError("MVP 仅支持 .xlsx 文件")
        output_dir = request.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        run_id = request.run_id or uuid.uuid4().hex[:12]
        return RunContext(
            run_id=run_id,
            a_path=a_path,
            b_path=b_path,
            output_dir=output_dir,
            c_path=output_dir / "C.xlsx",
            report_path=output_dir / "report.json",
            month=request.month,
            user_overrides=request.user_overrides,
        )
