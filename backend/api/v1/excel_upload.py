import json
from datetime import datetime
from pathlib import Path

from config import Config
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from agent.llm import ReconciliationLLMAgent
from agent.llm_providers import LLMProviderError
from agent.workflows.reconciliation.copy_a_to_c import copy_a_to_c_from_metadata
from agent.workflows.reconciliation.match_c_to_b import match_c_to_b_from_metadata
from backend.services.product_mapping_service import ProductMappingService
from tools import ExcelSheetPreview, excel_tool

router = APIRouter(
    prefix="/api/reconciliation",
    tags=["文件上传"],
)

# __file__：当前 Python 文件的路径，也就是 backend/api/v1/excel_upload.py
# Path(...)：把字符串路径转换成 pathlib.Path 对象，方便后面用 / 拼接路径
# resolve()：转换成绝对路径，避免相对路径受运行命令所在目录影响
# parents[2]：向上取第 3 层父目录：v1 -> api -> backend，所以这里得到 backend 目录
BASE_DIR = Path(__file__).resolve().parents[2]

# / 是 pathlib.Path 提供的路径拼接写法，等价于 os.path.join(BASE_DIR, "storage", "tasks")
# 最终目录是 backend/storage/tasks，用来存放每次上传生成的任务文件夹
TASKS_DIR = BASE_DIR / "storage" / "tasks"

# MVP 第一版只允许上传 .xlsx 文件
ALLOWED_SUFFIX = ".xlsx"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _validate_xlsx(file: UploadFile, label: str) -> None:
    # UploadFile.filename：用户上传文件时携带的原始文件名
    # or ""：如果 filename 是 None，就兜底成空字符串，避免后面处理时报错
    filename = file.filename or ""

    if not filename:
        # HTTPException：FastAPI 中断请求并返回指定 HTTP 状态码和错误信息
        raise HTTPException(status_code=400, detail=f"{label}文件名不能为空")

    # Path(filename).suffix：获取文件后缀，例如 “A.xlsx” 的 suffix 是 “.xlsx”
    # lower()：统一转成小写，这样 .XLSX / .xlsx 都能按同一规则判断
    if Path(filename).suffix.lower() != ALLOWED_SUFFIX:
        raise HTTPException(status_code=400, detail=f"{label}仅支持 .xlsx 文件")


def _new_task_id() -> str:
    # datetime.now()：获取当前本地时间
    # strftime(...)：把时间格式化成字符串
    # %Y%m%d%H%M%S%f 分别表示：年月日时分秒微秒，用微秒降低 task_id 重复概率
    return f"REC{datetime.now().strftime('%Y%m%d%H%M%S%f')}"  # noqa: DTZ005


def _resolve_task_dir(task_id: str) -> Path:
    task_dir = (TASKS_DIR / task_id).resolve()
    if not task_dir.is_relative_to(TASKS_DIR.resolve()) or not task_dir.is_dir():
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_dir


async def _save_upload(file: UploadFile, target: Path) -> None:
    try:
        # await file.read()：异步读取上传文件的全部二进制内容
        content = await file.read()

        if not content:
            raise HTTPException(status_code=400, detail=f"{file.filename} 文件内容为空")

        # write_bytes(...)：以二进制方式写入文件，适合保存 Excel、图片等非纯文本文件
        target.write_bytes(content)
    finally:
        # close()：关闭上传文件对象，释放临时文件/文件句柄资源
        # 放在 finally 中，确保即使中途报错也会执行关闭
        await file.close()


def _preview_to_response(preview: ExcelSheetPreview) -> dict[str, object]:
    """把 Excel 预览转成前端和 JSON 都能直接使用的结构。"""

    return {
        "sheet_name": preview.sheet_name,
        "max_row": preview.max_row,
        "max_column": preview.max_column,
        "rows": [
            {
                "row_number": row.row_number,
                "cells": [
                    {
                        "coordinate": cell.coordinate,
                        "column": cell.column,
                        "value": cell.display_text,
                        "python_type": cell.python_type,
                        "excel_data_type": cell.excel_data_type,
                        "number_format": cell.number_format,
                        "is_date": cell.is_date,
                    }
                    for cell in row.cells
                ],
            }
            for row in preview.rows
        ],
    }


def _parse_llm_json(text: str) -> dict[str, object]:
    """尽量把 LLM 的 JSON 答案解析出来；解析失败时保留原文。"""

    stripped = text.strip()
    if not stripped:
        return {"raw_text": ""}

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return {"raw_text": text}

    if isinstance(payload, dict):
        return payload
    return {"raw_text": text}


def _analyze_a_sheet_with_llm(a_file_path: Path) -> tuple[ExcelSheetPreview, dict[str, object]]:
    """解析 A 表预览并调用 LLM 判断数据行数。"""

    try:
        preview = excel_tool.read_sheet_preview(a_file_path, rows=8, max_columns=12)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"A表解析失败：{exc}") from exc

    try:
        # llm_response = ReconciliationLLMAgent(provider="deepseek").analyze_excel_preview(preview)
        # llm_response = ReconciliationLLMAgent(provider="deepseek",model="deepseek-v4-flash", base_url="https://api.deepseek.com", api_key_env="DEEPSEEK_API_KEY",).analyze_excel_preview(preview)
        llm_response = ReconciliationLLMAgent(provider="ollama").analyze_excel_preview(preview)
    except LLMProviderError as exc:
        raise HTTPException(status_code=500, detail=f"LLM 分析失败：{exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM 分析失败：{exc}") from exc

    llm_result = _parse_llm_json(llm_response.text)
    llm_result.setdefault("raw_text", llm_response.text)
    llm_result["model"] = llm_response.model
    llm_result["provider"] = llm_response.provider
    return preview, llm_result


def _build_product_mapping(a_file_path: Path, b_file_path: Path) -> dict[str, object]:
    """调用商品映射服务，生成 A/B 商品规格映射结果。"""

    try:
        # ProductMappingService(...)：创建商品映射服务，服务内部负责读列、去重、调用 LLM。
        service = ProductMappingService(
            llm_agent=ReconciliationLLMAgent(
                provider="deepseek",
                model="deepseek-v4-flash",
                base_url=Config.DEEPSEEK_BASE_URL,
                api_key_env="DEEPSEEK_API_KEY",
            )
        )
        # service = ProductMappingService(
        #     llm_agent=ReconciliationLLMAgent(provider="ollama")
        # )
        return service.build_product_mapping(a_file_path, b_file_path)
    except LLMProviderError as exc:
        raise HTTPException(status_code=500, detail=f"商品映射 LLM 分析失败：{exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"商品字段读取失败：{exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"商品映射生成失败：{exc}") from exc


def _read_metadata(metadata_path: Path) -> dict[str, object]:
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="任务元数据格式无效")
    return payload


def _write_metadata(metadata_path: Path, metadata: dict[str, object]) -> None:
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _latest_match_summary(metadata: dict[str, object]) -> dict[str, int]:
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


@router.post("/upload")
async def upload_excel(
    # File(...)：告诉 FastAPI 这个参数来自 multipart/form-data 文件上传
    # ... 表示必填；前端必须同时传 a_file 和 b_file
    a_file: UploadFile = File(...),  # noqa: B008
    b_file: UploadFile = File(...),  # noqa: B008
):
    # 校验 A 表和 B 表是否都是 .xlsx 文件
    _validate_xlsx(a_file, "A表")
    _validate_xlsx(b_file, "B表")

    # 为本次上传生成唯一任务 ID
    task_id = _new_task_id()

    # 拼出当前任务目录，例如 backend/storage/tasks/REC202608191234567890
    task_dir = TASKS_DIR / task_id

    # mkdir(...)：创建目录
    # parents=True：如果 backend/storage/tasks 不存在，就连同中间目录一起创建
    # exist_ok=False：如果 task_id 目录已存在就报错，避免覆盖旧任务
    task_dir.mkdir(parents=True, exist_ok=False)

    # A/B 文件保存成固定文件名，后续流程不用依赖用户原始文件名
    a_file_path = task_dir / "A.xlsx"
    b_file_path = task_dir / "B.xlsx"

    # 保存上传的 Excel 文件到任务目录
    await _save_upload(a_file, a_file_path)
    await _save_upload(b_file, b_file_path)

    # isoformat(...)：把时间转成 ISO 格式字符串，方便 JSON 保存和前端展示
    # timespec="seconds"：精确到秒，不保留微秒
    created_at = datetime.now().isoformat(timespec="seconds")  # noqa: DTZ005

    # metadata 用来临时记录任务信息；后续接 SQLite 后可以迁移到数据库表
    metadata = {
        "task_id": task_id,
        "status": "UPLOADED",
        # str(Path)：把 Path 对象转成字符串，便于写入 JSON
        "a_file_path": str(a_file_path),
        "b_file_path": str(b_file_path),
        "a_original_filename": a_file.filename,
        "b_original_filename": b_file.filename,
        "created_at": created_at,
    }

    preview, llm_result = _analyze_a_sheet_with_llm(a_file_path)
    metadata["a_preview"] = _preview_to_response(preview)
    metadata["llm_result"] = llm_result

    product_mapping = _build_product_mapping(a_file_path, b_file_path)
    metadata["product_mapping"] = product_mapping

    metadata_path = task_dir / "metadata.json"

    # json.dumps(...)：把 Python 字典转换成 JSON 字符串
    # ensure_ascii=False：保留中文，不转成 \uXXXX
    # indent=2：格式化缩进，便于人工查看
    # write_text(...)：以文本方式写入 metadata.json
    # encoding="utf-8"：使用 UTF-8 编码，避免中文乱码
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        c_file_path = copy_a_to_c_from_metadata(metadata_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"C表底稿生成失败：{exc}") from exc

    try:
        match_c_to_b_from_metadata(metadata_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"C表匹配与反向核查失败：{exc}") from exc

    latest_metadata = _read_metadata(metadata_path)
    latest_metadata["status"] = "SUCCESS"
    _write_metadata(metadata_path, latest_metadata)
    match_summary = _latest_match_summary(latest_metadata)

    # 返回给前端：上传请求同步完成 C 表生成、A/B 匹配和 B 表反向核查。
    return {
        "task_id": task_id,
        "status": latest_metadata["status"],
        "a_preview": latest_metadata["a_preview"],
        "llm_result": llm_result,
        "product_mapping": product_mapping,
        "c_file_path": str(c_file_path),
        "match_summary": match_summary,
    }


@router.get("/tasks/{task_id}/download/c-table")
async def download_c_table(task_id: str):
    task_dir = _resolve_task_dir(task_id)
    c_file_path = task_dir / "C.xlsx"
    if not c_file_path.exists():
        raise HTTPException(status_code=404, detail="C表文件不存在")

    return FileResponse(
        c_file_path,
        media_type=XLSX_MEDIA_TYPE,
        filename=f"{task_id}_C表.xlsx",
    )
