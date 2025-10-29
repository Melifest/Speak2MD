"""Сервис пайплайна: каркас.

Здесь будет реализация аудио → текст → обработка → LLM → Markdown/JSON.
Ответственный Сергеев А.П (и немного Саватин В.А.).
"""

from sqlalchemy.orm import Session
from ..models import Job

def run_job(db: Session, job: Job):
    """Запуск обработчика задачи.

    Каркас - реализовать позже.
    """
    raise NotImplementedError("Pipeline is not implemented yet")
