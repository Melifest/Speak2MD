tasks = {
    # Тестовая завершенная задача для демонстрации
    "completed-task-123": {
        "id": "completed-task-123",
        "status": "in progress",
        "progress": 0,
        "filename": "test-audio.mp3",
        "file_size": 1024000
    }
}


# Функция для обновления прогресса задачи
def update_task_progress(task_id: str, progress: int, status: str = None):
    """
    Обновляет прогресс задачи и уведомляет WebSocket клиентов
    """
    if task_id in tasks:
        tasks[task_id]["progress"] = progress
        if status:
            tasks[task_id]["status"] = status

        # Здесь позже добавим уведомление WebSocket клиентов
        print(f"Task {task_id} progress updated: {progress}%")