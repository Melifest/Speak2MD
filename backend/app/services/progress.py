"""Сервис прогресса: каркас.

Определяет интерфейсы для хранения прогресса и событий задач(БД/бродкаст событий и пр.).
"""

from sqlalchemy.orm import Session

def add_event(db: Session, job_id: str, event_type: str, payload: dict | None = None):
    """Записать событие задачи.

    Каркас - реализовать позже.
    """
    raise NotImplementedError("Progress add_event is not implemented yet")

def set_progress(db: Session, job_id: str, progress: int, status=None):
    """Обновить прогресс задачи.

    Каркас - реализовать позже.
    """
    raise NotImplementedError("Progress set_progress is not implemented yet")
