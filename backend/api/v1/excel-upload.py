from fastapi import APIRouter

router = APIRouter()

@router.post("/excel-upload")
def upload_excel():
    return {"message": "Excel upload endpoint"}