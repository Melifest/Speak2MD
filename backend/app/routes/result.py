from fastapi import APIRouter, HTTPException, status

router = APIRouter()

@router.get("/result/{job_id}")
def get_result_stub(job_id: str, format: str = "markdown"):
    """Каркас-эндпоинт результатов - реалзовать позже."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Result endpoint is not implemented yet")
