"""WebSocket endpoints for real-time task updates."""

import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for broadcasting task updates."""

    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected ({len(self.active_connections)} total)")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected ({len(self.active_connections)} remaining)")

    async def broadcast(self, event_type: str, payload: dict):
        """Broadcast an event to all connected clients."""
        message = json.dumps({"type": event_type, "payload": payload})
        stale = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as exc:
                logger.warning(f"WebSocket broadcast failed, removing client: {exc}")
                stale.add(connection)
        for s in stale:
            self.active_connections.discard(s)


manager = ConnectionManager()


async def broadcast_event(event_type: str, payload: dict):
    """Convenience function to broadcast an event via the connection manager.

    Imported by orchestrator_service to push events to connected frontends.
    """
    await manager.broadcast(event_type, payload)


@router.websocket("/events")
async def task_events(websocket: WebSocket):
    """WebSocket endpoint for real-time task and project updates.

    Clients connect to /ws/events and receive JSON messages:
      {"type": "task.updated", "payload": {"task_id": "...", "status": "review", ...}}
    """
    await manager.connect(websocket)
    try:
        # Keep the connection alive and listen for client messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Client sent a message — could be used for client-initiated actions
                msg = json.loads(data)
                # Echo back for confirmation
                await websocket.send_text(json.dumps({"type": "echo", "payload": msg}))
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception as exc:
                    logger.warning(f"WebSocket ping failed, ending session: {exc}")
                    break
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected gracefully")
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}", exc_info=True)
    finally:
        manager.disconnect(websocket)