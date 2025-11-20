from fastapi import APIRouter, HTTPException, status, Query, Header
from fastapi.responses import Response
from datetime import datetime, timedelta
import os
from pathlib import Path
import uuid
from ..db import SessionLocal
from ..models import Job, JobStatus, ShareLink
from ..utils.security import get_current_user
from ..utils.validation import validate_job_id
from ..services.storage import path_for

router = APIRouter()

# шеринг read-only: создать, посмотреть по токену, отозвать
@router.post("/share/{job_id}")
def create_share(job_id: str, authorization: str = Header(None)):
    job_id = validate_job_id(job_id)  #нормализуем/проверяем ууид
    user = get_current_user(authorization)
    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        job_status_value = job.status.value if isinstance(job.status, JobStatus) else str(job.status)
        if job_status_value != "ready":#делимся только готовым
            raise HTTPException(status_code=status.HTTP_425_TOO_EARLY, detail="Task is not completed yet")
        if not job.user_id or job.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        token = str(uuid.uuid4())#генерим простой uuid как токен
        expires_at = datetime.utcnow() + timedelta(days=7)
        sl = ShareLink(
            token=token,
            job_id=job_id,
            owner_id=user.id,
            expires_at=expires_at,
            revoked=False,
        )
        db.add(sl)
        db.commit()
        return {"url": f"/api/share/{token}", "expires_at": expires_at.isoformat()}# фронт подставит базовый url

@router.get("/share/{token}")
def get_share(token: str, format: str = Query("markdown", regex="^(markdown|json)$")):
    with SessionLocal() as db:
        sl = db.query(ShareLink).filter(ShareLink.token == token).first()
        if not sl:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
        if sl.revoked or sl.expires_at <= datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link expired or revoked")
        job = db.query(Job).filter(Job.id == sl.job_id).first()# на всякий проверим job
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        job_status_value = job.status.value if isinstance(job.status, JobStatus) else str(job.status)
        if job_status_value != "ready":# лишний случай — пока не готово
            raise HTTPException(status_code=status.HTTP_425_TOO_EARLY, detail="Task is not completed yet")
        if format == "markdown":  # обычный md результат
            if job.result_md_path:
                result_path = Path(job.result_md_path)
                filename = os.path.basename(job.result_md_path) or "result.md"
            else:
                result_path = path_for(sl.job_id, "result.md")
                filename = "result.md"
        else:# json: сначала путь из бд, потом стандарт, потом fallback на transcript.json
            if job.result_json_path:
                result_path = Path(job.result_json_path)
                filename = os.path.basename(job.result_json_path) or "result.json"
            else:
                result_path = path_for(sl.job_id, "result.json")
                filename = "result.json"
                if not result_path.exists():
                    alt_path = path_for(sl.job_id, "transcript.json")
                    if alt_path.exists():
                        result_path = alt_path
                        filename = "transcript.json"
        if not result_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result file not found")
        try:
            with open(result_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read result file: {str(e)}")
        media_type = "text/markdown; charset=utf-8" if format == "markdown" else "application/json"
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Job-ID": sl.job_id,
                "X-Filename": (job.original_filename or os.path.basename(str(result_path)))  # подсказка имени
            }
        )

@router.delete("/share/{token}")
def revoke_share(token: str, authorization: str = Header(None)):
    user = get_current_user(authorization)  # кто пытается отозвать
    with SessionLocal() as db:
        sl = db.query(ShareLink).filter(ShareLink.token == token).first()  # ищем ссылку
        if not sl:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
        if not (sl.owner_id == user.id or getattr(user, "role", "user") == "admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        sl.revoked = True
        db.add(sl)
        db.commit()
        return {"revoked": True}# фронту ок