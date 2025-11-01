from .ws_manager import broadcast_progress

# Существующее хранилище задач
tasks = {
    "completed-task-123": {
        "id": "completed-task-123",
        "status": "completed",
        "progress": 100,
        "filename": "test-audio.mp3",
        "file_size": 1024000
    }
}


def update_task_progress(task_id: str, progress: int, status: str = None, message: str = None):
    """Обновить прогресс задачи и уведомить WebSocket клиентов.
    Теперь рассылка выполняется всегда, даже если запись задачи отсутствовала ранее:
    создаём минимальную запись и продолжаем.
    """
    #обеспечим наличие записи задачи
    task = tasks.get(task_id)
    if not task:
        tasks[task_id] = {
            "id": task_id,
            "status": status or "processing",
            "progress": 0,
        }
        task = tasks[task_id]

    # Обновляем данные задачи
    task["progress"] = progress
    if status is not None:
        task["status"] = status
    if message is not None:
        task["message"] = message

        # подготавливаем для отправки
        progress_data = {
            "job_id": task_id,
            "progress": progress,
            "status": task.get("status"),
            "message": message or f"Processing... {progress}%"
        }

    # (в любом случае) уведомляем всех подключенных клиентов
    import asyncio
    try:
        # Пытаемся получить текущий event loop
        loop = asyncio.get_event_loop()
        # Если loop работает, создаем задачу
        if loop.is_running():
            asyncio.create_task(broadcast_progress(task_id, progress_data))
        else:
            # Если loop не запущен, запускаем и выполняем
            loop.run_until_complete(broadcast_progress(task_id, progress_data))
    except RuntimeError:
        # Если нет event loop (например, в отдельном потоке), создаем новый
        asyncio.run(broadcast_progress(task_id, progress_data))

    print(f"📊 Task {task_id} progress updated: {progress}%")