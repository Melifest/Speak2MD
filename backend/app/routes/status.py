from fastapi import APIRouter, HTTPException, status
from ..shared_storage import tasks
from ..schemas import StatusResponse  # ← Используем существующую модель
from ..db import SessionLocal
from ..models import Job, JobStatus

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

    job_id = job_id.strip()

    #1 - пытаемся взять из in-memory (WS прогресс, симулятор)
    task = tasks.get(job_id)
    if task:
        return StatusResponse(
            job_id=task["id"],
            status=task["status"],
            progress=task["progress"],
            message=task.get("message")
        )

    #2 - фоллбэк на БД (реальный пайплайн)
    try:
        with SessionLocal() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
    except Exception:
        job = None

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    #3-  Возвращаем статус из БД
    return StatusResponse(
        job_id=job.id,
        status=(job.status.value if isinstance(job.status, JobStatus) else str(job.status)),
        progress=int(job.progress or 0),
        message=job.error_message
    )