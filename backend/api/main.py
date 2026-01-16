"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import health, plugins, chat, audio, images
from .websocket.streaming import websocket_endpoint
from ..core.plugin_manager import PluginManager
from ..core.plugin_registry import PluginRegistry
from ..core.model_manager import ModelManager
from ..core.vram_monitor import VRAMMonitor

logger = logging.getLogger(__name__)

# Global instances
plugin_registry: PluginRegistry = None
plugin_manager: PluginManager = None
model_manager: ModelManager = None
vram_monitor: VRAMMonitor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global plugin_registry, plugin_manager, model_manager, vram_monitor
    
    # Startup
    logger.info("Starting application...")
    
    # Initialize core components
    vram_monitor = VRAMMonitor()
    model_manager = ModelManager(vram_monitor)
    plugin_registry = PluginRegistry()
    plugin_manager = PluginManager(plugin_registry)
    
    # Initialize plugins
    await plugin_manager.initialize_all()
    
    logger.info("Application started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Cleanup plugins
    if plugin_manager:
        await plugin_manager.cleanup_all()
    
    logger.info("Application shut down")


# Create FastAPI app
app = FastAPI(
    title="Multi-Agent AI System",
    description="Production-grade multi-agent AI platform with plugin architecture",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(plugins.router)
app.include_router(chat.router)
app.include_router(audio.router)
app.include_router(images.router)

# WebSocket endpoint
app.add_websocket_route("/ws", websocket_endpoint)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Multi-Agent AI System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
