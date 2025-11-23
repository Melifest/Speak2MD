"""Сервис хранения: каркас.

Определяет интерфейсы для работы с файловым хранилищем (локально, S3 и пр.).
"""

import os
from pathlib import Path

# базовая директория для хранения артекфактов
DATA_DIR = Path(os.getenv("DATA_DIR", "./data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

def job_dir(job_id: str) -> Path:
    """Вернуть путь к директории задачи - реализовано.
    """
    d=DATA_DIR/job_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def save_bytes(job_id: str, filename: str, data: bytes) -> Path:
    """Сохранить данные байтов в хранилище задачи - реализовано.
    """
    p=job_dir(job_id)/filename
    with open(p, "wb") as f:
        f.write(data)
    return p

def path_for(job_id: str, name: str) -> Path:
    """Получить путь к файлу артефакта - реализовано.
    """
    return job_dir(job_id)/name
