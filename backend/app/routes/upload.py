from fastapi import APIRouter, UploadFile, File, HTTPException, status
import uuid
import os
from ..schemas import UploadResponse, ErrorResponse

router = APIRouter()

# Временное хранилище (используем то же, что в status.py)
from ..shared_storage import tasks
from ..shared_storage import update_task_progress


@router.post("/upload", response_model=UploadResponse, responses={400: {"model": ErrorResponse}})
async def upload_audio(file: UploadFile = File(...)):
    """
    Загружает аудиофайл и создает задачу на обработку
    """

    # 1. Проверяем тип файла
    allowed_types = ['audio/mpeg', 'audio/mp4', 'audio/wav', 'audio/x-wav']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат файла. Разрешены: MP3, M4A, WAV"
        )

    # 2. Проверяем расширение файла (дополнительная проверка)
    allowed_extensions = ['.mp3', '.m4a', '.wav']
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

    # 6. Сохраняем информацию о задаче
    tasks[job_id] = {
        "id": job_id,
        "status": "processing",
        "progress": 0,
        "filename": file.filename,
        "file_size": file_size
    }

    update_task_progress(job_id, 0, "processing")

    print(f"✅ Создана задача {job_id} для файла {file.filename} ({file_size} байт)")

    # 7. Возвращаем ответ пользователю
    return UploadResponse(
        job_id=job_id,
        status="processing"
    )