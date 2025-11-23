import asyncio
import json
from ..shared_storage import tasks, update_task_progress
from ..services.storage import save_bytes
import logging
from pathlib import Path
from . import storage
from .audio_converter import convert_to_wav_16k_mono
from ..utils.markdown import render_markdown
# ВНИМАНИЕ - это вспомогательный файл без реального пайплайна, позже НУЖНО заменить на реальные вызовы пайпалйна
# Сейчас upload.py явно использует simulate_processing(job_id) . Если его удалить, надо обеспечить, что реальная 
# обработка будет вызывать update_task_progress , иначе прогресса не будет вообще.

logger = logging.getLogger("speak2md")

async def simulate_processing(job_id: str):
    """Имитирует процесс обработки файла с обновлением прогресса"""
    #находим original.* и конвертируем в audio16k.wav
    try:
        base_dir: Path = storage.job_dir(job_id)
        original = next(base_dir.glob("original.*"), None)
        if not original:
            update_task_progress(job_id, 0, "error", "Original file not found")
            logger.error("Original file not found for job %s", job_id)
            return

        update_task_progress(job_id, 5, "processing", "Converting to WAV 16k mono...")

        output = base_dir / "audio16k.wav"
        # таймаут конвертации (минимально прожиточный для mvp)
        convert_to_wav_16k_mono(original, output, timeout_sec=60)

        update_task_progress(job_id, 20, "processing", "Audio converted to WAV 16k mono")
    except Exception as e:
        #лог ошибки (внутри конвертера уже детали уже есть), выставляем статус error
        logger.exception("Conversion failed for job %s", job_id)
        update_task_progress(job_id, 0, "error", f"Conversion failed: {e}")
        return

    # Получаем данные задачи
    task_data = tasks.get(job_id)
    if not task_data:
        print(f"❌ Задача {job_id} не найдена в хранилище")
        return

    # Этапы обработки с сообщениями
    stages = [
        (40, "Speech recognition started"),
        (60, "Converting to text"),
        (80, "Structuring content"),
        (100, "Task completed!")
    ]

    for progress, message in stages:
        # Ждем перед следующим этапом
        await asyncio.sleep(2)

        # Обновляем прогресс
        status = "processing" if progress < 100 else "completed"
        update_task_progress(job_id, progress, status, message)

        print(f"📊 Progress updated for {job_id}: {progress}% - {message}")

    if progress == 100:  # После завершения обработки
        await create_test_results(job_id, task_data)


async def create_test_results(job_id: str, task_data: dict):
    """Создает тестовые файлы результатов для демонстрации"""

    transcript_text = (
        f"Файл {task_data['filename']} успешно обработан. Размер {task_data['file_size']} байт."
    )
    markdown_content = render_markdown(transcript_text, {"filename": task_data.get("filename")})

    # Создаем тестовый JSON результат
    json_content = {
        "job_id": job_id,
        "filename": task_data['filename'],
        "file_size": task_data['file_size'],
        "status": "completed",
        "sections": [
            {
                "title": "Основные тезисы",
                "content": [
                    "Аудиофайл успешно обработан",
                    f"Размер файла: {task_data['file_size']} байт",
                    "Качество распознавания: 95%"
                ]
            },
            {
                "title": "Ключевые решения",
                "content": [
                    "Релиз запланирован на следующую неделю",
                    "Добавить новую функциональность в API",
                    "Оптимизировать процесс обработки аудио"
                ]
            },
            {
                "title": "Action Items",
                "content": [
                    "Завершить интеграцию с фронтендом",
                    "Протестировать на различных аудиоформатах",
                    "Подготовить документацию для пользователей"
                ]
            }
        ],
        "metadata": {
            "processing_time": "2.5 секунды",
            "service": "Speak2MD",
            "version": "0.1.0"
        }
    }

    # Сохраняем файлы результатов
    try:
        save_bytes(job_id, "result.md", markdown_content.encode('utf-8'))
        save_bytes(job_id, "result.json", json.dumps(json_content, ensure_ascii=False, indent=2).encode('utf-8'))

        logger.info(f"Results saved for job {job_id}")
        logger.info(f"result.md - {len(markdown_content)} chars")
        logger.info(f"result.json - {len(json.dumps(json_content))} chars")

    except Exception as e:
        logger.error(f"Failed to save results for {job_id}: {e}")
