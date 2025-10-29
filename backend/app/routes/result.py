from fastapi import APIRouter, HTTPException, status
from ..schemas import ErrorResponse
from ..shared_storage import tasks

router = APIRouter()


@router.get("/result/{job_id}")
def get_result(job_id: str, format: str = "markdown"):
    """
    Получить результат обработки задачи

    - **job_id**: ID задачи
    - **format**: Формат результата (markdown или json)
    """

    # 1. Ищем задачу
    task = tasks.get(job_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # 2. Проверяем что задача завершена
    if task["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="Task is not completed yet"
        )

    # 3. Генерируем заглушку результата (позже заменим на реальные данные)
    if format == "markdown":
        # Возвращаем Markdown контент
        result_content = {task['filename']} # Заглушка
        return result_content
    
    elif format == "json":
        # Возвращаем JSON структуру заглушки
        return {
            "job_id": job_id,
            "filename": task["filename"],
            "status": task["status"],
            "content": {
                "title": f"Расшифровка: {task['filename']}",
                "sections": [
                    {
                        "heading": "Основные тезисы",
                        "bullets": [
                            "Это автоматически сгенерированная расшифровка",
                            f"Файл: {task['filename']}",
                            f"Размер: {task['file_size']} байт"
                        ]
                    },
                    {
                        "heading": "Содержание", 
                        "bullets": [
                            "Введение - основные моменты",
                            "Ключевые идеи - важные тезисы", 
                            "Заключение - итоги и выводы"
                        ]
                    }
                ],
                "metadata": {
                    "service": "Speak2MD",
                    "version": "0.1.0",
                    "note": "Демо-результат"
                }
            }
        }
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported format. Use 'markdown' or 'json'"
        )