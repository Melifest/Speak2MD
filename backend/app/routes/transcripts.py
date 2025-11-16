from fastapi import APIRouter, HTTPException, status, Query, Header
from typing import Optional
from pathlib import Path
import os
from ..db import SessionLocal
from ..models import Job, JobStatus
from ..utils.security import get_current_user
from ..services.storage import path_for, job_dir
from ..schemas import TranscriptItem, TranscriptListResponse

router = APIRouter()

# файл - витрина для транскриптов. По факту читаем Job + файлы
# как-будто есть сущность Transcript. Без отдельной таблицы.
# Почему не реализовали транскрипт? Потому-что это излишне, Job уже вполне все функции реализует, 
# достаточно делать правильный запрос с списком джобов - а оттуда файлы.


@router.get("/transcripts", response_model=TranscriptListResponse)
def list_transcripts(
    authorization: str = Header(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    # тянем текущего юзера из Bearer
    user = get_current_user(authorization)
    with SessionLocal() as db:
        # фильтруем только свои задачи и только готовые (ready)
        q = (
            db.query(Job)
            .filter(Job.user_id == user.id, Job.status == JobStatus.ready)
            .order_by(Job.created_at.desc())
        )
        # считаем общий размер - для MVP норм, потом можно сделать count отдельно
        total = q.count()
        jobs = q.offset(offset).limit(limit).all()

        items = []
        for j in jobs:
            # title берём из исходного имени файла, if нет - фоллбэк
            title = j.original_filename or f"Transcript {j.id}"
            items.append(
                TranscriptItem(
                    id=j.id,
                    title=title,
                    created_at=j.created_at,
                    duration_sec=j.duration_seconds,
                    status=j.status.value if hasattr(j.status, "value") else str(j.status),
                )
            )

        return TranscriptListResponse(total=total, items=items)


@router.get("/transcripts/{job_id}")
def get_transcript(
    job_id: str,
    authorization: str = Header(None),
    format: Optional[str] = Query("meta"),
):
    # проверка, что этот job принадлежит текущему пользователю
    user = get_current_user(authorization)
    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")

    md_path = path_for(job_id, "result.md")
    json_path = path_for(job_id, "result.json")

    if format == "markdown":
        # отдаём файл как текст, контент возвращаем строкой, тип ставит FastAPI
        if not md_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Markdown not found")
        return open(md_path, "r", encoding="utf-8").read()

    if format == "json":
        # отдаём json; if его нет - 404 (норм для некоторых пайплайнов)
        if not json_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="JSON not found")
        return open(json_path, "r", encoding="utf-8").read()

    # meta-режим: возвращаем только метаданные и ссылки, без контента
    title = job.original_filename or f"Transcript {job.id}"
    content_url = f"/api/result/{job_id}"
    json_url = content_url if json_path.exists() else None
    return {
        "id": job.id,
        "title": title,
        "created_at": job.created_at.isoformat(),
        "content_url": content_url,
        "json_url": json_url,
    }


@router.delete("/transcripts/{job_id}")
def delete_transcript(job_id: str, authorization: str = Header(None)):
    # удаление только своего. если не мой — 404 (чтоб лишнего не раскрывать)
    user = get_current_user(authorization)
    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
        db.delete(job)
        db.commit()

    d = job_dir(job_id)
    try:
        # аккуратно чистим директорию с артефактами, не падаем на мелких ошибках
        if d.exists():
            for p in d.glob("**/*"):
                try:
                    p.unlink()
                except Exception:
                    pass
            try:
                d.rmdir()
            except Exception:
                pass
    except Exception:
        pass

    return {"deleted": True}