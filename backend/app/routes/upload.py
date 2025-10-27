from fastapi import APIRouter, HTTPException, status
from ..schemas import UploadResponse, ErrorResponse

router = APIRouter()
@router.post("/upload", response_model=UploadResponse, responses={501: {"model": ErrorResponse}})
def upload_stub():
    """Каркас-эндпоинт загрузки - реализовать позже."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Upload endpoint is not implemented yet")
