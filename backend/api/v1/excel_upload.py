from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.domain.errors import (
    BadRequestError,
    ExternalServiceError,
    ReconciliationError,
    TaskNotFoundError,
    WorkflowExecutionError,
)
from backend.services.reconciliation_task_service import (
    ReconciliationTaskService,
    UploadedWorkbook,
)

router = APIRouter(
    prefix="/api/reconciliation",
    tags=["文件上传"],
)

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _read_upload(file: UploadFile) -> UploadedWorkbook:
    try:
        return UploadedWorkbook(
            filename=file.filename or "",
            content=await file.read(),
        )
    finally:
        await file.close()


def _to_http_exception(exc: ReconciliationError) -> HTTPException:
    if isinstance(exc, BadRequestError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, TaskNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ExternalServiceError | WorkflowExecutionError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.post("/upload")
async def upload_excel(
    a_file: UploadFile = File(...),  # noqa: B008
    b_file: UploadFile = File(...),  # noqa: B008
):
    service = ReconciliationTaskService()
    try:
        return service.create_reconciliation_task(
            await _read_upload(a_file),
            await _read_upload(b_file),
        )
    except ReconciliationError as exc:
        raise _to_http_exception(exc) from exc


@router.get("/tasks/{task_id}/download/c-table")
async def download_c_table(task_id: str):
    service = ReconciliationTaskService()
    try:
        c_file_path = service.get_c_table_path(task_id)
    except ReconciliationError as exc:
        raise _to_http_exception(exc) from exc

    if not c_file_path.exists():
        raise HTTPException(status_code=404, detail="C表文件不存在")

    return FileResponse(
        c_file_path,
        media_type=XLSX_MEDIA_TYPE,
        filename=service.build_download_filename(task_id),
    )
