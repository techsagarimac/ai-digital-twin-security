from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.camera_service import runtime
from app.ws.manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/live")
async def live_feed(ws: WebSocket) -> None:
    """Live detections, boxes, landmarks, attributes, events, and JPEG frames."""
    await manager.connect(ws)
    try:
        await ws.send_json({"type": "hello", **runtime.snapshot_status()})
        if runtime.latest_frame:
            await ws.send_json(runtime.latest_frame)
        while True:
            # Keep the socket open; the camera thread pushes frames.
            await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:
        await manager.disconnect(ws)
