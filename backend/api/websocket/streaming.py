"""WebSocket streaming handler."""

import json
import logging
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

from ...core.orchestrator import Orchestrator, RequestType
from ...core.plugin_manager import PluginManager
from ...core.plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for streaming."""
    
    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: list[WebSocket] = []
        registry = PluginRegistry()
        plugin_manager = PluginManager(registry)
        self.orchestrator = Orchestrator(plugin_manager)
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected WebSockets."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)


# Global WebSocket manager
ws_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming."""
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            # Parse request
            request_type_str = data.get("request_type", "text")
            content = data.get("content", "")
            metadata = data.get("metadata", {})
            
            # Map request type
            request_type_map = {
                "text": RequestType.TEXT,
                "audio": RequestType.AUDIO,
                "image": RequestType.IMAGE,
                "video": RequestType.VIDEO
            }
            req_type = request_type_map.get(request_type_str, RequestType.TEXT)
            
            # Process request and stream results
            async for chunk in ws_manager.orchestrator.process_request(
                req_type,
                content,
                metadata
            ):
                await ws_manager.send_personal_message({
                    "type": chunk.get("type", "text"),
                    "content": chunk.get("content", ""),
                    "metadata": chunk.get("metadata", {})
                }, websocket)
            
            # Send done signal
            await ws_manager.send_personal_message({
                "type": "done",
                "content": "",
                "metadata": {}
            }, websocket)
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
