import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..shared_storage import tasks

router = APIRouter()

# Хранилище активных подключений
active_connections = {}


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket для отслеживания прогресса задачи в реальном времени
    """

    # Принимаем подключение
    await websocket.accept()

    # Добавляем подключение в активные
    if job_id not in active_connections:
        active_connections[job_id] = []
    active_connections[job_id].append(websocket)

    try:
        # Отправляем начальное состояние
        task = tasks.get(job_id)
        if task:
            await websocket.send_json({
                "event": "status_update",
                "data": {
                    "status": task["status"],
                    "progress": task["progress"],
                    "message": "Connected to task progress"
                }
            })
        else:
            await websocket.send_json({
                "event": "error",
                "data": {
                    "message": f"Task {job_id} not found"
                }
            })
            await websocket.close()
            return

        # Имитируем прогресс обработки (ПОЗЖЕ ЗАМЕНИМ НА РЕАЛЬНЫЙ ПРОГРЕСС ИЗ ML-ПАЙПЛАЙНА)
        if task["status"] == "processing":
            for progress in range(task["progress"] + 10, 101, 10):
                # Обновляем прогресс в общем хранилище
                task["progress"] = progress

                # Если достигли 100% - помечаем как завершенную
                if progress == 100:
                    task["status"] = "completed"
                    # Отправляем финальное сообщение о завершении
                    await websocket.send_json({
                        "event": "completed",
                        "data": {
                            "progress": 100,
                            "status": "completed",
                            "message": "Task completed successfully",
                            "result_url": f"/api/result/{job_id}"
                        }
                    })
                    break  # Выходим из цикла прогресса
                else:
                    # Отправляем обычное обновление прогресса
                    message = {
                        "event": "progress_update",
                        "data": {
                            "progress": progress,
                            "status": task["status"],
                            "message": f"Processing... {progress}%"
                        }
                    }
                    await websocket.send_json(message)

                # Ждем перед следующим обновлением (имитация работы)
                await asyncio.sleep(2)

        # Если задача уже завершена, отправляем финальный статус
        elif task["status"] == "completed":
            await websocket.send_json({
                "event": "completed",
                "data": {
                    "progress": 100,
                    "status": "completed",
                    "message": "Task completed successfully",
                    "result_url": f"/api/result/{job_id}"
                }
            })

        # Держим соединение открытым для получения сообщений от клиента
        while True:
            try:
                # Ждем сообщения от клиента (например, ping)
                data = await websocket.receive_text()

                # Обрабатываем ping/pong
                if data == "ping":
                    await websocket.send_text("pong")

            except WebSocketDisconnect:
                # Клиент отключился - выходим из цикла
                break

    except WebSocketDisconnect:
        # Клиент отключился во время обработки
        print(f"Client disconnected from task {job_id}")

    except Exception as e:
        # Обрабатываем другие ошибки
        error_message = f"WebSocket error: {str(e)}"
        print(error_message)
        try:
            await websocket.send_json({
                "event": "error",
                "data": {"message": error_message}
            })
        except:
            pass  # Клиент уже отключился

    finally:
        # Убираем подключение из активных
        if job_id in active_connections and websocket in active_connections[job_id]:
            active_connections[job_id].remove(websocket)
            if not active_connections[job_id]:
                del active_connections[job_id]