from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ws/{job_id}")
async def ws_stub(websocket: WebSocket, job_id: str):
    """Каркас-WebSocket - реализовать позже."""
    await websocket.accept()
    await websocket.send_json({"event": "error", "data": {"message": "WebSocket endpoint is not implemented yet"}})
    await websocket.close()
