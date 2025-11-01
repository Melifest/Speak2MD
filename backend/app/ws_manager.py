from typing import Dict, List
from fastapi import WebSocket
import logging

logger = logging.getLogger("speak2md")

# Хранилище активных подключений: job_id -> list of WebSocket
_connections: Dict[str, List[WebSocket]] = {}


async def connect(job_id: str, websocket: WebSocket):
    """Добавить WebSocket подключение для задачи"""
    await websocket.accept()
    if job_id not in _connections:
        _connections[job_id] = []
    _connections[job_id].append(websocket)
    logger.info(f"WebSocket connected for job {job_id}, total connections: {len(_connections[job_id])}")


def disconnect(job_id: str, websocket: WebSocket):
    """Удалить WebSocket подключение"""
    if job_id in _connections:
        if websocket in _connections[job_id]:
            _connections[job_id].remove(websocket)
            logger.info(f"WebSocket disconnected for job {job_id}, remaining: {len(_connections[job_id])}")

        # Удаляем пустой список подключений
        if not _connections[job_id]:
            del _connections[job_id]
            logger.info(f"No more connections for job {job_id}")


async def broadcast_progress(job_id: str, progress_data: dict):
    """Отправить обновление прогресса всем подключенным клиентам"""
    if job_id not in _connections:
        return

    message = {
        "event": "progress",
        "data": progress_data
    }

    dead_connections = []

    # Отправляем сообщение всем активным подключениям
    for websocket in _connections[job_id]:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket for job {job_id}: {e}")
            dead_connections.append(websocket)

    # Удаляем мертвые подключения
    for websocket in dead_connections:
        disconnect(job_id, websocket)