"""
WebSocket Connection Manager and Real-Time Event Dispatcher.
Enables bidirectional streaming between Unity Simulator, AI Pipeline, and Trainee Dashboard (Section 18).
"""

import json
from typing import List, Dict, Any, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts telemetry events."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and registers incoming WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes disconnected WebSocket client."""
        self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcasts a JSON message to all connected clients (Unity / Dashboard)."""
        payload = json.dumps(message)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.active_connections.discard(dead)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Bidirectional WebSocket endpoint for real-time telemetry:
    - Unity streams camera events / frame metadata
    - AI Engine broadcasts detections and tracking updates
    - Trainee Dashboard receives live radar/threat feeds
    """
    await manager.connect(websocket)
    try:
        # Send initial connection handshake
        await websocket.send_json({
            "event": "connected",
            "message": "Connected to Drone Threat Trainer Telemetry Hub",
            "active_clients": len(manager.active_connections)
        })

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Echo / broadcast event across all subscribers
                await manager.broadcast(message)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
