"""
websocket_manager.py — WebSocket connection manager for real-time browser updates.

Manages connected WebSocket clients and broadcasts market data updates,
alerts, regime shifts, and portfolio metrics in real time.
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections and broadcasts updates to all clients.
    Thread-safe for use with the streaming engine's background threads.
    """

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket disconnected. Total clients: {len(self.active_connections)}")

    async def _send_to_client(self, websocket: WebSocket, message: str):
        """Send a message to a single client, removing if disconnected."""
        try:
            await websocket.send_text(message)
        except Exception:
            self.disconnect(websocket)

    async def _broadcast_async(self, message: str):
        """Broadcast a message to all connected clients (async)."""
        with self._lock:
            connections = list(self.active_connections)

        disconnected = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    def broadcast(self, event_type: str, data: dict):
        """
        Thread-safe broadcast from background threads.
        Packages data with event type and timestamp, then schedules
        the async broadcast on the event loop.
        """
        if not self.active_connections:
            return

        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, default=str)

        # Schedule on the event loop
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._broadcast_async(message), self._loop
            )

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the asyncio event loop for scheduling broadcasts."""
        self._loop = loop

    @property
    def client_count(self) -> int:
        return len(self.active_connections)


# Global instance
ws_manager = ConnectionManager()
