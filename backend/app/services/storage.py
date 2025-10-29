"""Сервис хранения: каркас.

Определяет интерфейсы для работы с файловым хранилищем (локально, S3 и пр.).
"""

from pathlib import Path

def job_dir(job_id: str) -> Path:
    """Вернуть путь к директории задачи - реализовать позже.
    """
    raise NotImplementedError("Storage job_dir is not implemented yet")

def save_bytes(job_id: str, filename: str, data: bytes) -> Path:
    """Сохранить данные байтов в хранилище задачи - реализовать позже.
    """
    raise NotImplementedError("Storage save_bytes is not implemented yet")

def path_for(job_id: str, name: str) -> Path:
    """Получить путь к файлу артефакта - реализовать позже.
    """
    raise NotImplementedError("Storage path_for is not implemented yet")
