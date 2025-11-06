from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import Response
import os
from pathlib import Path
from ..shared_storage import tasks
from ..services.storage import path_for
from ..db import SessionLocal
from ..models import Job, JobStatus

router = APIRouter()


@router.get("/result/{job_id}")
async def get_result(
        job_id: str,
        format: str = Query("markdown", regex="^(markdown|json)$")
):
    """
    Получить результат обработки для job
  - job_id: UUID задания на обработку
  - format: формат результата - markdown или json
  - return: рзультат обработки в запрашиваемом формате
    """

    # 1. Валидация job_id
    if not job_id or not job_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job ID cannot be empty"
        )

    job_id = job_id.strip()

    # 2. Пытаемся взять из in-memory (WS прогресс, симулятор)
    task = tasks.get(job_id)
    if task:
        # допускаем оба финальных статуса: completed (симулятор) + ready (реальный пайплайн)
        if task.get("status") not in {"completed", "ready"}:
            raise HTTPException(
                status_code=status.HTTP_425_TOO_EARLY,
                detail="Task is not completed yet"
            )

        # Определяем путь к файлу результата
        filename = "result.md" if format == "markdown" else "result.json"
        result_path = path_for(job_id, filename)

        # Для JSON поддерживаем артефакт из реального пайплайна: transcript.json
        if format == "json" and not result_path.exists():
            alt_path = path_for(job_id, "transcript.json")
            if alt_path.exists():
                result_path = alt_path
                filename = "transcript.json"

        # Проверяем что файл существует
        if not result_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Result file not found for job {job_id}"
            )

        # Читаем содержимое файла
        try:
            with open(result_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read result file: {str(e)}"
            )

        media_type = "text/markdown; charset=utf-8" if format == "markdown" else "application/json"

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Job-ID": job_id,
                "X-Filename": task.get("filename") or os.path.basename(str(result_path))
            }
        )

    # 3. Fallback: пытаемся получить статус и пути из БД (реальный пайплайн)
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

    # Разрешаем результаты только для финального статуса "ready"
    job_status_value = job.status.value if isinstance(job.status, JobStatus) else str(job.status)
    if job_status_value != "ready":
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="Task is not completed yet"
        )

    # Определяем путь к результату: сначала поля из БД, затем артефакты в job_dir
    if format == "markdown":
        if job.result_md_path:
            result_path = Path(job.result_md_path)
            filename = os.path.basename(job.result_md_path) or "result.md"
        else:
            result_path = path_for(job_id, "result.md")
            filename = "result.md"
    else:
        # JSON: сначала job.result_json_path, затем result.json, затем transcript.json
        if job.result_json_path:
            result_path = Path(job.result_json_path)
            filename = os.path.basename(job.result_json_path) or "result.json"
        else:
            result_path = path_for(job_id, "result.json")
            filename = "result.json"
            if not result_path.exists():
                alt_path = path_for(job_id, "transcript.json")
                if alt_path.exists():
                    result_path = alt_path
                    filename = "transcript.json"

    if not result_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result file not found for job {job_id}"
        )

    try:
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read result file: {str(e)}"
        )

    media_type = "text/markdown; charset=utf-8" if format == "markdown" else "application/json"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Job-ID": job_id,
            "X-Filename": (job.original_filename or os.path.basename(str(result_path)))
        }
    )
