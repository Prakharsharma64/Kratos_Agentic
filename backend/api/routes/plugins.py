"""Plugin management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List

from ..schemas import PluginInfo
from ...core.plugin_manager import PluginManager
from ...core.plugin_registry import PluginRegistry

router = APIRouter(prefix="/plugins", tags=["plugins"])


def get_plugin_manager() -> PluginManager:
    """Dependency to get plugin manager."""
    from ...core.plugin_manager import PluginManager
    from ...core.plugin_registry import PluginRegistry
    registry = PluginRegistry()
    return PluginManager(registry)


@router.get("/", response_model=Dict[str, PluginInfo])
async def list_plugins(
    plugin_manager: PluginManager = Depends(get_plugin_manager)
) -> Dict[str, PluginInfo]:
    """List all plugins."""
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
    
    return plugins_info


@router.get("/{plugin_name}", response_model=PluginInfo)
async def get_plugin(
    plugin_name: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager)
) -> PluginInfo:
    """Get plugin information."""
    health = plugin_manager.get_plugin_health(plugin_name)
    
    if health.get("status") == "not_loaded":
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")
    
    metadata = health.get("metadata", {})
    return PluginInfo(
        name=plugin_name,
        type=metadata.get("type", "unknown"),
        version=metadata.get("version", "unknown"),
        status=health.get("status", "unknown"),
        healthy=health.get("healthy", False),
        vram_usage_gb=health.get("vram_usage_gb", 0.0),
        dependencies=metadata.get("dependencies", [])
    )


@router.post("/{plugin_name}/reload")
async def reload_plugin(
    plugin_name: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager)
) -> Dict[str, str]:
    """Reload a plugin."""
    try:
        await plugin_manager.reload_plugin(plugin_name)
        return {"status": "success", "message": f"Plugin {plugin_name} reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
