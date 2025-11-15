from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..ws_manager import connect, disconnect
import logging
logger = logging.getLogger("speak2md")

router = APIRouter()


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket для отслеживания прогресса задачи в реальном времени
    """
    # подключаем клиента
    await connect(job_id, websocket)

    try:
        # Держим соединение открытым
        while True:
            # ожидаем любые сообщения от клиента
            data = await websocket.receive_text()

            # Обрабатываем ping/pong
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from task {job_id}")
    except Exception as e:
        logger.warning(f"WebSocket error for task {job_id}: {e}")
    finally:
        disconnect(job_id, websocket)
