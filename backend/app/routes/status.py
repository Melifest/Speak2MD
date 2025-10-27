from fastapi import APIRouter, HTTPException, status
from ..schemas import StatusResponse

router = APIRouter()

@router.get("/status/{job_id}", response_model=StatusResponse, responses={501: {"description": "Not Implemented"}})
def get_status_stub(job_id: str):
    """Каркас-эндпоинт статуса - реализовать позже."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Status endpoint is not implemented yet")

@router.get("/status/{job_id}/sse")
async def stream_status_stub(job_id: str):
    """Каркас-SSE - реализовать позже."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="SSE endpoint is not implemented yet")
