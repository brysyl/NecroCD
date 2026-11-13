from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from events import broadcaster

router = APIRouter(tags=["telemetry"])


class PoltergeistTest(BaseModel):
    cause: str = "test failure"
    trace: str


@router.get("/api/telemetry")
async def recent():
    return [e.model_dump() for e in broadcaster.history]


@router.post("/api/telemetry/poltergeist")
async def trigger(body: PoltergeistTest):
    return (await broadcaster.poltergeist(body.cause, body.trace)).model_dump()


@router.websocket("/ws/telemetry")
async def ws_telemetry(ws: WebSocket):
    await broadcaster.connect(ws)
    await broadcaster.emit("hello", {"message": "The spirits are listening."})
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(ws)
