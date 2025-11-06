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
from ..services.processing_simulator import simulate_processing
from ..services.pipeline import run_job


@router.post("/upload", response_model=UploadResponse, responses={400: {"model": ErrorResponse}})
async def upload_audio(file: UploadFile = File(...)):
    """
    Загружает аудиофайл и создает задачу на обработку
    """

    # 1. Проверяем тип файла
    allowed_types = ['audio/mpeg', 'audio/mp4', 'audio/wav', 'audio/x-wav', 'audio/webm', 'audio/ogg']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат файла. Разрешены: MP3, M4A, WAV, WEBM, OGG"
        )

    # 2. Проверяем расширение файла (дополнительная проверка)
    allowed_extensions = ['.mp3', '.m4a', '.wav', '.webm', '.ogg']
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемое расширение файла. Разрешены: {', '.join(allowed_extensions)}"
        )

    # 3. Читаем файл чтобы определить размер
    content = await file.read()
    file_size = len(content)

    # 4. Проверяем размер файла (50 МБ = 50 * 1024 * 1024 байт)
    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл слишком большой. Максимальный размер: 50 МБ"
        )

    # 5. Создаем уникальный ID задачи
    job_id = str(uuid.uuid4())
    #5.1 сохраним исходный файл как original.<ext>
    original_name = f"original{file_extension}"
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

    # 6. Сохраняем информацию о задаче
    tasks[job_id] = {
        "id": job_id,
        "status": "processing",
        "progress": 0,
        "filename": file.filename,
        "file_size": file_size
    }


    update_task_progress(job_id, 0, "processing", "File uploaded, starting processing")

    print(f"✅ Создана задача {job_id} для файла {file.filename} ({file_size} байт)")

    # Запускаем реальную обработку в фоне (исполнитель в отдельном потоке)
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