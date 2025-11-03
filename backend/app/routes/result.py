from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from ..db import SessionLocal
from ..models import Job
from ..services import storage
from pathlib import Path

router = APIRouter()

@router.get("/result/{job_id}")
def get_result(job_id: str, format: str = "markdown"):
    #Возвращает результат обработки: markdown или json.
    fmt = (format or "markdown").lower()
    if fmt not in {"markdown", "json"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported format")

    #попыткка получить запись из БД
    job = None
    try:
        with SessionLocal() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
    except Exception:
        job = None

    # определение пути к файлу
    if job and fmt == "markdown" and job.result_md_path:
        path = Path(job.result_md_path)
    elif job and fmt == "json" and job.result_json_path:
        path = Path(job.result_json_path)
    else:
        # на всякий случай
        base_dir = storage.job_dir(job_id)
        path = base_dir / ("result.md" if fmt == "markdown" else "transcript.json")

    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    media_type = "text/markdown" if fmt == "markdown" else "application/json"
    return FileResponse(path, media_type=media_type)
