from fastapi import APIRouter, UploadFile, File, HTTPException, status
import uuid
import os
import asyncio
from ..schemas import UploadResponse, ErrorResponse
from ..db import SessionLocal
from ..models import Job, JobStatus

router = APIRouter()

# Временное хранилище (используем то же, что в status.py)
from ..shared_storage import tasks, update_task_progress
from ..services import storage
from ..services.pipeline import run_job
import logging
logger = logging.getLogger("speak2md")


@router.post("/upload", response_model=UploadResponse, responses={400: {"model": ErrorResponse}})
async def upload_audio(file: UploadFile = File(...)):
    #загружает аудиофайл и создает задачу на обработку


    # 1. проверка типа файла (нормализуем)
    raw_content_type = (file.content_type or '').strip().lower()
    normalized_content_type = raw_content_type.split(';', 1)[0].strip()
    allowed_types = ['audio/mpeg', 'audio/mp4', 'audio/wav', 'audio/x-wav', 'audio/webm', 'audio/ogg']
    if normalized_content_type not in allowed_types:
        # разрешение неизвестного типа, если допустимо (на фаерфокс не получалось записать)
        file_extension_check = os.path.splitext(file.filename)[1].lower()
        allowed_extensions_check = ['.mp3', '.m4a', '.wav', '.webm', '.ogg']
        if file_extension_check not in allowed_extensions_check:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неподдерживаемый формат файла. Разрешены: MP3, M4A, WAV, WEBM, OGG"
            )

    # 2. корректное расширение на основе content type + мягкая проверка расширения файла из имени
    allowed_extensions = ['.mp3', '.m4a', '.wav', '.webm', '.ogg']
    content_type_to_ext = {
        'audio/mpeg': '.mp3',
        'audio/mp4': '.m4a',
        'audio/wav': '.wav',
        'audio/x-wav': '.wav',
        'audio/webm': '.webm',
        'audio/ogg': '.ogg',
    }
    file_extension = os.path.splitext(file.filename)[1].lower()
    content_extension = content_type_to_ext.get(normalized_content_type)

    # if имя файла без допустимого расширения, но content-type поддерживаемый — продолжаем,
    # иначе - жоско отклоняем.
    if file_extension not in allowed_extensions and content_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемое расширение файла. Разрешены: {', '.join(allowed_extensions)}"
        )

    # 3. Чтение файла для определение размера
    content = await file.read()
    file_size = len(content)

    # 4. Проверить размер файла
    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл слишком большой. Максимальный размер: 50 МБ"
        )

    # 5. ID задачи
    job_id = str(uuid.uuid4())
    #5.1 сохраним исходный файл как original.<ext>,
    #<ext> определяется из content-type, а при его отсутствии — из имени
    save_ext = content_extension or (file_extension if file_extension in allowed_extensions else '.wav')
    original_name = f"original{save_ext}"
    storage.save_bytes(job_id, original_name, content)

    # 5.2 создание записи задачи в БД
    try:
        with SessionLocal() as db:
            job = Job(
                id=job_id,
                status=JobStatus.processing,
                progress=0,
                original_filename=file.filename,
                content_type=file.content_type,
            )
            db.add(job)
            db.commit()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB error: {e}")

    # 6.Сохраняем информацию о задаче
    tasks[job_id] = {
        "id": job_id,
        "status": "processing",
        "progress": 0,
        "filename": file.filename,
        "file_size": file_size
    }


    update_task_progress(job_id, 0, "processing", "File uploaded, starting processing")

    logger.info(f"Job {job_id} created for file {file.filename} ({file_size} bytes)")

    #запускаем реальную обработку в фоне
    async def _process_job_async(job_id: str):
        def _sync():
            try:
                with SessionLocal() as db:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if job:
                        run_job(db, job)
            except Exception as e:
                update_task_progress(job_id, 0, "error", f"Background processing failed: {e}")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _sync)

    asyncio.create_task(_process_job_async(job_id))

    # 7. Возвращаем ответ пользователю
    return UploadResponse(
        job_id=job_id,
        status="processing"
    )
