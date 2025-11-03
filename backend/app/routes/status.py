from fastapi import APIRouter, HTTPException, status
from ..shared_storage import tasks
from ..schemas import StatusResponse  # ← Используем существующую модель

router = APIRouter()


@router.get(
    "/status/{job_id}",
    response_model=StatusResponse,
    responses={
        200: {"description": "Status retrieved successfully"},
        404: {"description": "Job not found"},
        422: {"description": "Validation error"}
    }
)
def get_status(job_id: str):
    """
    Get processing status for a job

    - **job_id**: UUID of the processing job
    - **returns**: Current status and progress percentage
    """

    # Простая валидация (можно вынести позже если понадобится)
    if not job_id or not job_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job ID cannot be empty"
        )

    # Ищем задачу в хранилище
    task = tasks.get(job_id.strip())

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Возвращаем статус задачи
    return StatusResponse(
        job_id=task["id"],
        status=task["status"],
        progress=task["progress"],
        message=task.get("message")  # Будет None если нет сообщения
    )