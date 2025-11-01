from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..ws_manager import connect, disconnect

router = APIRouter()


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket для отслеживания прогресса задачи в реальном времени
    """
    # Подключаем клиента
    await connect(job_id, websocket)

    try:
        # Держим соединение открытым
        while True:
            # Ожидаем любые сообщения от клиента (ping и т.д.)
            data = await websocket.receive_text()

            # Обрабатываем ping/pong
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        # Клиент отключился - нормальное завершение
        print(f"Client disconnected from task {job_id}")
    except Exception as e:
        # Другие ошибки
        print(f"WebSocket error for task {job_id}: {e}")
    finally:
        # Всегда убираем подключение при выходе
        disconnect(job_id, websocket)