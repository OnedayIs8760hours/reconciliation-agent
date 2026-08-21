"""后端对账任务服务。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from agent.domain.config import ReconciliationRunRequest
from agent.domain.statuses import TaskStatus
from agent.workflows.c_table_workflow import CTableWorkflow

BASE_DIR = Path(__file__).resolve().parents[1]
TASKS_DIR = BASE_DIR / "storage" / "tasks"


def task_dir(task_id: str) -> Path:
    path = TASKS_DIR / task_id
    if not path.exists():
        raise HTTPException(status_code=404, detail="任务不存在")
    return path


def metadata_path(task_id: str) -> Path:
    return task_dir(task_id) / "metadata.json"


def read_metadata(task_id: str) -> dict[str, Any]:
    path = metadata_path(task_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="任务元数据不存在")
    return json.loads(path.read_text(encoding="utf-8"))


def write_metadata(task_id: str, metadata: dict[str, Any]) -> None:
    metadata_path(task_id).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def run_task(task_id: str, month: str) -> dict[str, Any]:
    metadata = read_metadata(task_id)
    if metadata.get("status") not in {TaskStatus.UPLOADED.value, TaskStatus.FAILED.value, TaskStatus.SUCCESS.value}:
        raise HTTPException(status_code=409, detail="任务正在处理中")
    metadata.update({"status": TaskStatus.PROCESSING.value, "month": month, "started_at": datetime.now().isoformat(timespec="seconds")})
    write_metadata(task_id, metadata)

    output_dir = task_dir(task_id) / "output"
    report = CTableWorkflow().run(
        ReconciliationRunRequest(
            a_file=Path(metadata["a_file_path"]),
            b_file=Path(metadata["b_file_path"]),
            month=month,
            output_dir=output_dir,
            run_id=task_id,
        )
    )
    final_status = TaskStatus.SUCCESS.value if report.status == "passed" else TaskStatus.FAILED.value
    metadata.update(
        {
            "status": final_status,
            "c_file_path": str(report.c_file) if report.c_file else None,
            "report_file_path": str(report.report_file),
            "error_message": "；".join(report.errors),
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    write_metadata(task_id, metadata)
    return build_task_response(metadata, report.model_dump(mode="json"))


def get_task(task_id: str) -> dict[str, Any]:
    metadata = read_metadata(task_id)
    report_payload: dict[str, Any] | None = None
    report_path = metadata.get("report_file_path")
    if report_path and Path(report_path).exists():
        report_payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
    return build_task_response(metadata, report_payload)


def download_path(task_id: str, kind: str) -> Path:
    metadata = read_metadata(task_id)
    field = "c_file_path" if kind == "c" else "report_file_path"
    path_value = metadata.get(field)
    if not path_value:
        raise HTTPException(status_code=404, detail="文件尚未生成")
    path = Path(path_value)
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return path


def build_task_response(metadata: dict[str, Any], report: dict[str, Any] | None = None) -> dict[str, Any]:
    task_id = metadata["task_id"]
    status = metadata.get("status", TaskStatus.UPLOADED.value)
    month = metadata.get("month", "")
    verification = (report or {}).get("verification", {})
    matching = (report or {}).get("matching", {})
    coverage = (report or {}).get("coverage", {})
    exceptions = (report or {}).get("exceptions", [])
    success = status == TaskStatus.SUCCESS.value
    failed = status == TaskStatus.FAILED.value
    steps = [
        {"id": 1, "title": "文件检查", "status": "done" if status != TaskStatus.UPLOADED.value else "active"},
        {"id": 2, "title": "生成 C 表底稿", "status": "done" if success or failed else "pending"},
        {"id": 3, "title": "A/B 数据匹配", "status": "done" if success or failed else "pending"},
        {"id": 4, "title": "B 表反向核查", "status": "done" if success or failed else "pending"},
        {"id": 5, "title": "最终验收", "status": "done" if success else "failed" if failed else "pending"},
    ]
    return {
        "id": task_id,
        "title": f"{task_id} · {month or '待选择月份'}对账",
        "targetName": "对账任务",
        "month": month,
        "status": status,
        "aFile": {"name": metadata.get("a_original_filename", "A.xlsx"), "size": "", "uploaded": True},
        "bFile": {"name": metadata.get("b_original_filename", "B.xlsx"), "size": "", "uploaded": True, "recognized": True},
        "progressSteps": steps,
        "progressDetail": {
            "currentText": "核查通过，生成文件可下载" if success else metadata.get("error_message") or "任务已失败" if failed else "等待运行",
            "progress": 100 if success or failed else 10,
            "processedCRecords": matching.get("a_record_count", 0),
            "totalCRecords": matching.get("a_record_count", 0),
            "matchedBRecords": matching.get("matched_a_rows", 0),
            "manualReviewCount": len(exceptions),
        },
        "verifyMetrics": [
            {"label": "A/C 数量差额", "value": verification.get("qty_diff", "-"), "passed": verification.get("qty_diff", 1) == 0, "hint": "数量口径核查"},
            {"label": "A/C 金额差额", "value": verification.get("amount_diff", "-"), "passed": verification.get("amount_diff", 1) == 0, "hint": "金额口径核查"},
            {"label": "B表未解释记录", "value": verification.get("unexplained_b_records", "-"), "passed": verification.get("unexplained_b_records", 1) == 0, "hint": "反向覆盖核查"},
            {"label": "Excel公式错误", "value": verification.get("formula_error_count", "-"), "passed": verification.get("formula_error_count", 1) == 0, "hint": "公式检查"},
        ],
        "coverage": {
            "monthlyRecords": coverage.get("b_record_count", 0),
            "acceptedByC": coverage.get("covered_b_records", 0),
            "markedMissing": coverage.get("appended_b_records", 0),
            "manuallyExcluded": coverage.get("manual_excluded_b_records", 0),
            "unexplained": coverage.get("unexplained_b_records", 0),
        },
        "exceptions": exceptions,
        "downloads": [
            {"id": "c-table", "name": "C.xlsx", "type": "excel", "enabled": bool(metadata.get("c_file_path"))},
            {"id": "verify-report", "name": "report.json", "type": "report", "enabled": bool(metadata.get("report_file_path"))},
        ],
        "createdAt": metadata.get("created_at", ""),
        "completedAt": metadata.get("finished_at"),
    }
