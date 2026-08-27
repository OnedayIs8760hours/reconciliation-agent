from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agent.llm import ReconciliationLLMAgent
from agent.llm_providers import LLMProviderError
from agent.workflows.reconciliation.copy_a_to_c import copy_a_to_c_from_metadata
from agent.workflows.reconciliation.match_c_to_b import match_c_to_b_from_metadata
from backend.config import Config
from backend.domain.errors import BadRequestError, ExternalServiceError, WorkflowExecutionError
from backend.domain.json_parser import parse_json_object
from backend.repositories.task_repository import TaskRepository
from backend.schemas.reconciliation import preview_to_response
from backend.services.product_mapping_service import ProductMappingService
from tools import ExcelSheetPreview, excel_tool

ALLOWED_SUFFIX = ".xlsx"


@dataclass(frozen=True)
class UploadedWorkbook:
    filename: str
    content: bytes


class ReconciliationTaskService:
    """Application service that coordinates upload, LLM analysis, and workflows."""

    def __init__(self, repository: TaskRepository | None = None) -> None:
        self.repository = repository or TaskRepository()

    def get_c_table_path(self, task_id: str) -> Path:
        return self.repository.c_table_path(task_id)

    def build_download_filename(self, task_id: str) -> str:
        return f"{task_id}_C表.xlsx"

    def create_reconciliation_task(
        self,
        a_upload: UploadedWorkbook,
        b_upload: UploadedWorkbook,
    ) -> dict[str, object]:
        self.validate_upload(a_upload, "A表")
        self.validate_upload(b_upload, "B表")

        task_id = self.repository.new_task_id()
        task_dir = self.repository.create_task_dir(task_id)
        a_file_path = task_dir / "A.xlsx"
        b_file_path = task_dir / "B.xlsx"

        self.repository.save_bytes(a_file_path, a_upload.content)
        self.repository.save_bytes(b_file_path, b_upload.content)

        created_at = datetime.now().isoformat(timespec="seconds")  # noqa: DTZ005
        metadata: dict[str, object] = {
            "task_id": task_id,
            "status": "UPLOADED",
            "a_file_path": str(a_file_path),
            "b_file_path": str(b_file_path),
            "a_original_filename": a_upload.filename,
            "b_original_filename": b_upload.filename,
            "created_at": created_at,
        }

        preview, llm_result = self.analyze_a_sheet_with_llm(a_file_path)
        metadata["a_preview"] = preview_to_response(preview)
        metadata["llm_result"] = llm_result

        product_mapping = self.build_product_mapping(a_file_path, b_file_path)
        metadata["product_mapping"] = product_mapping

        metadata_path = self.repository.metadata_path(task_dir)
        self.repository.write_metadata(metadata_path, metadata)

        c_file_path = self.create_c_draft(metadata_path)
        self.match_c_to_b(metadata_path)

        latest_metadata = self.repository.read_metadata(metadata_path)
        latest_metadata["status"] = "SUCCESS"
        self.repository.write_metadata(metadata_path, latest_metadata)

        return {
            "task_id": task_id,
            "status": latest_metadata["status"],
            "a_preview": latest_metadata["a_preview"],
            "llm_result": llm_result,
            "product_mapping": product_mapping,
            "c_file_path": str(c_file_path),
            "match_summary": self.repository.latest_match_summary(latest_metadata),
        }

    def validate_upload(self, upload: UploadedWorkbook, label: str) -> None:
        if not upload.filename:
            raise BadRequestError(f"{label}文件名不能为空")
        if Path(upload.filename).suffix.lower() != ALLOWED_SUFFIX:
            raise BadRequestError(f"{label}仅支持 .xlsx 文件")
        if not upload.content:
            raise BadRequestError(f"{upload.filename} 文件内容为空")

    def analyze_a_sheet_with_llm(self, a_file_path: Path) -> tuple[ExcelSheetPreview, dict[str, object]]:
        try:
            preview = excel_tool.read_sheet_preview(a_file_path, rows=8, max_columns=12)
        except Exception as exc:
            raise BadRequestError(f"A表解析失败：{exc}") from exc

        try:
            llm_response = ReconciliationLLMAgent(
                provider=Config.PREVIEW_LLM_PROVIDER,  # type: ignore[arg-type]
                model=Config.PREVIEW_LLM_MODEL,
                base_url=Config.PREVIEW_LLM_BASE_URL,
                api_key_env=Config.PREVIEW_LLM_API_KEY_ENV,
            ).analyze_excel_preview(preview)
        except LLMProviderError as exc:
            raise ExternalServiceError(f"LLM 分析失败：{exc}") from exc
        except Exception as exc:
            raise ExternalServiceError(f"LLM 分析失败：{exc}") from exc

        llm_result = parse_json_object(llm_response.text) or {"raw_text": llm_response.text}
        llm_result.setdefault("raw_text", llm_response.text)
        llm_result["model"] = llm_response.model
        llm_result["provider"] = llm_response.provider
        return preview, llm_result

    def build_product_mapping(self, a_file_path: Path, b_file_path: Path) -> dict[str, object]:
        try:
            service = ProductMappingService(
                llm_agent=ReconciliationLLMAgent(
                    provider=Config.MAPPING_LLM_PROVIDER,  # type: ignore[arg-type]
                    model=Config.MAPPING_LLM_MODEL,
                    base_url=Config.MAPPING_LLM_BASE_URL,
                    api_key_env=Config.MAPPING_LLM_API_KEY_ENV,
                )
            )
            return service.build_product_mapping(a_file_path, b_file_path)
        except LLMProviderError as exc:
            raise ExternalServiceError(f"商品映射 LLM 分析失败：{exc}") from exc
        except ValueError as exc:
            raise BadRequestError(f"商品字段读取失败：{exc}") from exc
        except Exception as exc:
            raise WorkflowExecutionError(f"商品映射生成失败：{exc}") from exc

    def create_c_draft(self, metadata_path: Path) -> Path:
        try:
            return copy_a_to_c_from_metadata(metadata_path)
        except Exception as exc:
            raise WorkflowExecutionError(f"C表底稿生成失败：{exc}") from exc

    def match_c_to_b(self, metadata_path: Path) -> None:
        try:
            match_c_to_b_from_metadata(metadata_path)
        except Exception as exc:
            raise WorkflowExecutionError(f"C表匹配与反向核查失败：{exc}") from exc
