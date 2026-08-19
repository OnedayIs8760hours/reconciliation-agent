from fastapi import APIRouter

from backend.api.v1.excel_upload import router as excel_upload_router

router = APIRouter()
router.include_router(excel_upload_router)
