from fastapi import APIRouter

from backend.api.v1.excel_upload import router as excel_upload_router
from backend.api.v1.reconciliation import router as reconciliation_router

router = APIRouter()
router.include_router(excel_upload_router)
router.include_router(reconciliation_router)
