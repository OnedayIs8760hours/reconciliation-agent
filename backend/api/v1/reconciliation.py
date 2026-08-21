"""对账任务 API。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.services.reconciliation_service import download_path, get_task, run_task

router = APIRouter(prefix="/api/reconciliation", tags=["对账任务"])


class RunRequest(BaseModel):
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")


@router.post("/{task_id}/run")
def run_reconciliation(task_id: str, body: RunRequest):
    return run_task(task_id, body.month)


@router.get("/{task_id}")
def get_reconciliation_task(task_id: str):
    return get_task(task_id)


@router.get("/{task_id}/download/{kind}")
def download_reconciliation_file(task_id: str, kind: str):
    if kind not in {"c", "report"}:
        raise HTTPException(status_code=400, detail="仅支持 c 或 report")
    path = download_path(task_id, kind)
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if kind == "c" else "application/json"
    filename = Path(path).name
    return FileResponse(path, media_type=media_type, filename=filename)
