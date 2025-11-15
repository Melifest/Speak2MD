from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..ws_manager import connect, disconnect

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
        # клиент отключился - нормальное завершение
        print(f"Client disconnected from task {job_id}")
    except Exception as e:
        # Другие ошибки
        print(f"WebSocket error for task {job_id}: {e}")
    finally:
        disconnect(job_id, websocket)