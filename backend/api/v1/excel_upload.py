from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from agent.llm_providers import LLMProviderError
from backend.services.reconciliation_task_service import ReconciliationTaskService

router = APIRouter(
    prefix="/api/reconciliation",
    tags=["文件上传"],
)

# __file__：当前 Python 文件的路径，也就是 backend/api/v1/excel_upload.py。
# Path(...)：把字符串路径转换成 pathlib.Path 对象，方便后面用 / 拼接路径。
# resolve()：转换成绝对路径，避免相对路径受运行命令所在目录影响。
# parents[2]：向上取第 3 层父目录：v1 -> api -> backend，所以这里得到 backend 目录。
BASE_DIR = Path(__file__).resolve().parents[2]

# / 是 pathlib.Path 提供的路径拼接写法，等价于 os.path.join(BASE_DIR, "storage", "tasks")。
# 最终目录是 backend/storage/tasks，用来存放每次上传生成的任务文件夹。
TASKS_DIR = BASE_DIR / "storage" / "tasks"

# 目前正式流程只允许上传 .xlsx 文件，避免旧版 xls 解析样式和公式时出现兼容问题。
ALLOWED_SUFFIX = ".xlsx"

DOWNLOAD_FILES = {
    "c-table": {
        "file_name": "C.xlsx",
        "download_name": "C表.xlsx",
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    "b-marked": {
        "file_name": "B_marked.xlsx",
        "download_name": "B表缺失标注.xlsx",
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    "verify-report": {
        "file_name": "verify_report.json",
        "download_name": "核查报告.json",
        "media_type": "application/json",
    },
}


def _validate_xlsx(file: UploadFile, label: str) -> None:
    """校验上传文件必须是 xlsx。"""

    # UploadFile.filename：用户上传文件时携带的原始文件名。
    # or ""：如果 filename 是 None，就兜底成空字符串，避免后面处理时报错。
    filename = file.filename or ""

    if not filename:
        # HTTPException：FastAPI 中断请求并返回指定 HTTP 状态码和错误信息。
        raise HTTPException(status_code=400, detail=f"{label}文件名不能为空")

    # Path(filename).suffix：获取文件后缀，例如 “A.xlsx” 的 suffix 是 “.xlsx”。
    # lower()：统一转成小写，这样 .XLSX / .xlsx 都能按同一规则判断。
    if Path(filename).suffix.lower() != ALLOWED_SUFFIX:
        raise HTTPException(status_code=400, detail=f"{label}仅支持 .xlsx 文件")


def _new_task_id() -> str:
    """生成新的对账任务编号。"""

    # datetime.now()：获取当前本地时间。
    # strftime(...)：把时间格式化成字符串，用微秒降低 task_id 重复概率。
    return f"REC{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def _get_task_file_path(task_id: str, file_type: str) -> tuple[Path, str, str]:
    """根据任务编号和文件类型返回允许下载的文件路径。"""

    if file_type not in DOWNLOAD_FILES:
        raise HTTPException(status_code=404, detail="不支持的下载文件类型")

    file_info = DOWNLOAD_FILES[file_type]
    task_dir = TASKS_DIR / task_id
    file_path = task_dir / file_info["file_name"]

    # resolve()：把路径转成绝对路径，下面用来确认没有逃出任务根目录。
    tasks_root = TASKS_DIR.resolve()
    resolved_path = file_path.resolve()
    if tasks_root not in resolved_path.parents:
        raise HTTPException(status_code=400, detail="非法下载路径")

    if not resolved_path.exists():
        raise HTTPException(status_code=404, detail="任务文件不存在")

    return resolved_path, file_info["download_name"], file_info["media_type"]


@router.post("/upload")
async def upload_excel(
    # File(...)：告诉 FastAPI 这个参数来自 multipart/form-data 文件上传。
    a_file: UploadFile = File(...),
    b_file: UploadFile = File(...),
    # Form(...)：告诉 FastAPI 这个参数来自 multipart/form-data 普通字段。
    month: str = Form(...),
):
    """上传 A/B 表并直接执行完整正式对账流程。"""

    _validate_xlsx(a_file, "A表")
    _validate_xlsx(b_file, "B表")

    if not month:
        raise HTTPException(status_code=400, detail="对账月份不能为空")

    task_id = _new_task_id()
    service = ReconciliationTaskService(TASKS_DIR)

    try:
        # run_upload_task(...)：保存文件并编排字段识别、C 表生成、匹配、反向核查和强制验收。
        return await service.run_upload_task(task_id, a_file, b_file, month)
    except LLMProviderError as exc:
        raise HTTPException(status_code=500, detail=f"LLM 分析失败：{exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"对账任务执行失败：{exc}") from exc


@router.get("/tasks/{task_id}/files/{file_type}")
def download_task_file(task_id: str, file_type: str):
    """下载 C 表、B 表缺失标注或核查报告。"""

    file_path, download_name, media_type = _get_task_file_path(task_id, file_type)
    # FileResponse(...)：由 FastAPI 以文件流方式返回结果文件。
    return FileResponse(file_path, media_type=media_type, filename=download_name)
