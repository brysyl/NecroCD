"""WebSocket broadcaster for telemetry events."""
import asyncio
import logging
from typing import Optional

from fastapi import WebSocket

from models import TelemetryEvent
from poltergeist import translate_trace

log = logging.getLogger("necrocd.events")


class Broadcaster:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.history: list[TelemetryEvent] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def emit(self, type_: str, payload: Optional[dict] = None) -> TelemetryEvent:
        event = TelemetryEvent(type=type_, payload=payload or {})
        self.history.append(event)
        del self.history[:-200]
        for ws in list(self.clients):
            try:
                await ws.send_json(event.model_dump())
            except Exception:  # dead socket
                self.disconnect(ws)
        return event

    async def poltergeist(self, cause: str, trace: str, severity: str = "high") -> TelemetryEvent:
        return await self.emit(
            "poltergeist",
            {"cause": cause, "original": trace, "latin": translate_trace(trace), "severity": severity},
        )


broadcaster = Broadcaster()
