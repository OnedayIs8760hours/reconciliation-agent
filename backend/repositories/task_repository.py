from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.domain.errors import TaskNotFoundError, WorkflowExecutionError

BACKEND_DIR = Path(__file__).resolve().parents[1]
TASKS_DIR = BACKEND_DIR / "storage" / "tasks"


class TaskRepository:
    """File-backed repository for uploaded reconciliation task artifacts."""

    def __init__(self, tasks_dir: Path = TASKS_DIR) -> None:
        self.tasks_dir = tasks_dir

    def new_task_id(self) -> str:
        return f"REC{datetime.now().strftime('%Y%m%d%H%M%S%f')}"  # noqa: DTZ005

    def create_task_dir(self, task_id: str) -> Path:
        task_dir = self.tasks_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=False)
        return task_dir

    def resolve_task_dir(self, task_id: str) -> Path:
        root = self.tasks_dir.resolve()
        task_dir = (self.tasks_dir / task_id).resolve()
        if not task_dir.is_relative_to(root) or not task_dir.is_dir():
            raise TaskNotFoundError("任务不存在")
        return task_dir

    def c_table_path(self, task_id: str) -> Path:
        return self.resolve_task_dir(task_id) / "C.xlsx"

    def metadata_path(self, task_dir: Path) -> Path:
        return task_dir / "metadata.json"

    def save_bytes(self, file_path: Path, content: bytes) -> None:
        file_path.write_bytes(content)

    def read_metadata(self, metadata_path: Path) -> dict[str, Any]:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise WorkflowExecutionError("任务元数据格式无效")
        return payload

    def write_metadata(self, metadata_path: Path, metadata: dict[str, Any]) -> None:
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def latest_match_summary(self, metadata: dict[str, Any]) -> dict[str, int]:
        steps = metadata.get("workflow_steps")
        if not isinstance(steps, list):
            return {}

        for step in reversed(steps):
            if not isinstance(step, dict) or step.get("step") != "02_match_c_to_b":
                continue
            summary = step.get("summary")
            if not isinstance(summary, dict):
                return {}
            return {str(key): int(value) for key, value in summary.items() if isinstance(value, int)}
        return {}
