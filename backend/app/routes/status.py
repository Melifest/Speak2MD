from fastapi import APIRouter, HTTPException, status
from ..schemas import StatusResponse

router = APIRouter()

# ВРЕМЕННОЕ ХРАНИЛИЩЕ - позже заменим на базу данных
from ..shared_storage import tasks


@router.get("/status/{job_id}", response_model=StatusResponse)
def get_status(job_id: str):
    """Получить статус задачи по ID"""

    # Ищем задачу в нашем временном хранилище
    task = tasks.get(job_id)

    if not task:
        # Если задача не найдена - возвращаем ошибку 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Возвращаем данные в формате StatusResponse
    return {
        "job_id": task["id"],
        "status": task["status"],
        "progress": task["progress"]
    }