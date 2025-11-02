import asyncio
import logging
from pathlib import Path
from ..shared_storage import update_task_progress
from . import storage
from .audio_converter import convert_to_wav_16k_mono
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
        logger.info("Progress updated for %s: %s%% - %s", job_id, progress, message)