from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import Response
import os
from pathlib import Path
from ..shared_storage import tasks
from ..services.storage import path_for

router = APIRouter()


@router.get("/result/{job_id}")
async def get_result(
        job_id: str,
        format: str = Query("markdown", regex="^(markdown|json)$")
):
    """
    Get processing result for a job

    - **job_id**: UUID of the processing job
    - **format**: Result format - markdown or json
    - **returns**: Processing result in requested format
    """

    # 1. Валидация job_id
    if not job_id or not job_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job ID cannot be empty"
        )

    job_id = job_id.strip()

    # 2. Проверяем что задача существует и завершена
    task = tasks.get(job_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    if task["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="Task is not completed yet"
        )

    # 3. Определяем путь к файлу результата
    filename = "result.md" if format == "markdown" else "result.json"
    result_path = path_for(job_id, filename)

    # 4. Проверяем что файл существует
    if not result_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result file not found for job {job_id}"
        )

    # 5. Читаем содержимое файла
    try:
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read result file: {str(e)}"
        )

    # 6. Возвращаем результат в правильном формате
    media_type = "text/markdown; charset=utf-8" if format == "markdown" else "application/json"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Job-ID": job_id,
            "X-Filename": task["filename"]
        }
    )