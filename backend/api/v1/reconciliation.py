from fastapi import APIRouter

router = APIRouter()

@router.get("/reconciliation")
def tes1():
    return {"message": "Reconciliation endpoint"}