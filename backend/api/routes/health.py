"""Health check endpoints."""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..schemas import HealthResponse, PluginInfo
from ...core.plugin_manager import PluginManager
from ...core.vram_monitor import VRAMMonitor
from ...core.model_manager import ModelManager

router = APIRouter(prefix="/health", tags=["health"])


def get_plugin_manager() -> PluginManager:
    """Dependency to get plugin manager."""
    # TODO: Get from app state
    from ...core.plugin_manager import PluginManager
    from ...core.plugin_registry import PluginRegistry
    registry = PluginRegistry()
    return PluginManager(registry)


def get_vram_monitor() -> VRAMMonitor:
    """Dependency to get VRAM monitor."""
    # TODO: Get from app state
    from ...core.vram_monitor import VRAMMonitor
    return VRAMMonitor()


@router.get("/", response_model=HealthResponse)
async def health_check(
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    vram_monitor: VRAMMonitor = Depends(get_vram_monitor)
) -> HealthResponse:
    """Health check endpoint."""
    # Get plugin health
    plugin_health = plugin_manager.get_all_plugin_health()
    
    plugins_info = {}
    for name, health in plugin_health.items():
        plugins_info[name] = PluginInfo(
            name=name,
            type=health.get("metadata", {}).get("type", "unknown"),
            version=health.get("metadata", {}).get("version", "unknown"),
            status=health.get("status", "unknown"),
            healthy=health.get("healthy", False),
            vram_usage_gb=health.get("vram_usage_gb", 0.0),
            dependencies=health.get("metadata", {}).get("dependencies", [])
        )
    
    # Get VRAM status
    vram_summary = vram_monitor.get_summary()
    
    # Determine overall status
    all_healthy = all(h.get("healthy", False) for h in plugin_health.values())
    status = "healthy" if all_healthy else "degraded"
    
    return HealthResponse(
        status=status,
        plugins=plugins_info,
        vram=vram_summary
    )


@router.get("/plugins")
async def get_plugins_health(
    plugin_manager: PluginManager = Depends(get_plugin_manager)
) -> Dict[str, Any]:
    """Get all plugins health status."""
    return plugin_manager.get_all_plugin_health()


@router.get("/vram")
async def get_vram_status(
    vram_monitor: VRAMMonitor = Depends(get_vram_monitor)
) -> Dict[str, Any]:
    """Get VRAM status."""
    return vram_monitor.get_summary()
