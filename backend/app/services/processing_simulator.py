import asyncio
from ..shared_storage import update_task_progress


async def simulate_processing(job_id: str):
    """Имитирует процесс обработки файла с обновлением прогресса"""

    # Этапы обработки с сообщениями
    stages = [
        (10, "Processing audio..."),
        (25, "Speech recognition started"),
        (40, "Converting to text"),
        (60, "Structuring content"),
        (80, "Generating Markdown"),
        (100, "Task completed!")
    ]

    for progress, message in stages:
        # Ждем перед следующим этапом
        await asyncio.sleep(2)

        # Обновляем прогресс
        status = "processing" if progress < 100 else "completed"
        update_task_progress(job_id, progress, status, message)

        print(f"📊 Progress updated for {job_id}: {progress}% - {message}")