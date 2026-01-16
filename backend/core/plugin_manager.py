"""Plugin lifecycle management and dependency injection."""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict, deque

from .plugin_base import PluginBase, PluginType
from .plugin_registry import PluginRegistry
from .config import get_config

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin lifecycle and dependencies."""
    
    def __init__(self, registry: Optional[PluginRegistry] = None):
        """Initialize plugin manager.
        
        Args:
            registry: Plugin registry instance (creates new if None)
        """
        self.registry = registry or PluginRegistry()
        self.config = get_config()
        self.loaded_plugins: Dict[str, PluginBase] = {}
        self.plugin_instances: Dict[str, PluginBase] = {}
        self._initialization_order: List[str] = []
        self._lock = asyncio.Lock()
        
        # Discover plugins
        self.registry.discover_plugins()
    
    async def initialize_all(self) -> None:
        """Initialize all enabled plugins."""
        async with self._lock:
            enabled = set(self.config.plugins.enabled)
            disabled = set(self.config.plugins.disabled)
            
            # Get all plugin classes
            all_plugins = self.registry.get_all_plugins()
            
            # Filter by enabled/disabled
            plugins_to_load = {
                name: cls for name, cls in all_plugins.items()
                if name in enabled or (not enabled and name not in disabled)
            }
            
            # Resolve dependencies and get initialization order
            init_order = self._resolve_dependencies(plugins_to_load)
            
            # Initialize in order
            for plugin_name in init_order:
                if plugin_name in plugins_to_load:
                    try:
                        await self._initialize_plugin(plugin_name, plugins_to_load[plugin_name])
                    except Exception as e:
                        logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
                        # Continue with other plugins (graceful degradation)
    
    def _resolve_dependencies(self, plugins: Dict[str, type]) -> List[str]:
        """Resolve plugin dependencies and return initialization order.
        
        Args:
            plugins: Dictionary of plugin names to classes
            
        Returns:
            List of plugin names in initialization order
        """
        # Build dependency graph
        graph = defaultdict(set)
        in_degree = defaultdict(int)
        
        for name, cls in plugins.items():
            in_degree[name] = 0
            for dep in cls.dependencies:
                if dep in plugins:
                    graph[dep].add(name)
                    in_degree[name] += 1
                else:
                    logger.warning(f"Plugin {name} depends on {dep} which is not available")
        
        # Topological sort (Kahn's algorithm)
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for circular dependencies
        if len(result) != len(plugins):
            remaining = set(plugins.keys()) - set(result)
            raise ValueError(f"Circular dependency detected involving: {remaining}")
        
        return result
    
    async def _initialize_plugin(self, plugin_name: str, plugin_class: type) -> None:
        """Initialize a single plugin.
        
        Args:
            plugin_name: Plugin name
            plugin_class: Plugin class
        """
        if plugin_name in self.plugin_instances:
            logger.debug(f"Plugin {plugin_name} already initialized")
            return
        
        # Get plugin configuration
        plugin_config = self._get_plugin_config(plugin_name)
        
        # Create plugin instance
        plugin_instance = plugin_class()
        
        # Inject dependencies
        self._inject_dependencies(plugin_instance, plugin_class.dependencies)
        
        # Initialize plugin
        await plugin_instance.initialize(plugin_config)
        
        # Store instance
        self.plugin_instances[plugin_name] = plugin_instance
        self.loaded_plugins[plugin_name] = plugin_instance
        self._initialization_order.append(plugin_name)
        
        logger.info(f"Initialized plugin: {plugin_name}")
    
    def _inject_dependencies(self, plugin_instance: PluginBase, dependencies: List[str]) -> None:
        """Inject dependencies into a plugin instance.
        
        Args:
            plugin_instance: Plugin instance
            dependencies: List of dependency plugin names
        """
        for dep_name in dependencies:
            if dep_name not in self.plugin_instances:
                raise ValueError(f"Dependency {dep_name} not initialized for {plugin_instance.plugin_name}")
            
            # Set dependency as attribute (simple injection)
            setattr(plugin_instance, f"{dep_name}_plugin", self.plugin_instances[dep_name])
    
    def _get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a plugin.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Plugin configuration dictionary
        """
        # Get metadata
        metadata = self.registry.get_plugin_metadata(plugin_name) or {}
        config_schema = metadata.get("config_schema", {})
        
        # Build config from schema defaults
        config = {}
        for key, schema in config_schema.items():
            if "default" in schema:
                config[key] = schema["default"]
        
        # TODO: Load from config.yaml plugin-specific section
        
        return config
    
    async def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """Get a plugin instance.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Plugin instance or None
        """
        return self.plugin_instances.get(plugin_name)
    
    async def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginBase]:
        """Get all plugins of a specific type.
        
        Args:
            plugin_type: Plugin type
            
        Returns:
            List of plugin instances
        """
        return [
            plugin for plugin in self.plugin_instances.values()
            if plugin.plugin_type == plugin_type
        ]
    
    async def cleanup_all(self) -> None:
        """Cleanup all plugins."""
        async with self._lock:
            # Cleanup in reverse initialization order
            for plugin_name in reversed(self._initialization_order):
                if plugin_name in self.plugin_instances:
                    try:
                        await self.plugin_instances[plugin_name].cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up plugin {plugin_name}: {e}")
            
            self.plugin_instances.clear()
            self.loaded_plugins.clear()
            self._initialization_order.clear()
    
    async def reload_plugin(self, plugin_name: str) -> None:
        """Reload a plugin.
        
        Args:
            plugin_name: Plugin name
        """
        async with self._lock:
            # Cleanup existing instance
            if plugin_name in self.plugin_instances:
                await self.plugin_instances[plugin_name].cleanup()
                del self.plugin_instances[plugin_name]
                if plugin_name in self.loaded_plugins:
                    del self.loaded_plugins[plugin_name]
                if plugin_name in self._initialization_order:
                    self._initialization_order.remove(plugin_name)
            
            # Reinitialize
            plugin_class = self.registry.get_plugin_class(plugin_name)
            if plugin_class:
                await self._initialize_plugin(plugin_name, plugin_class)
    
    def get_plugin_health(self, plugin_name: str) -> Dict[str, Any]:
        """Get health status of a plugin.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Health status dictionary
        """
        if plugin_name not in self.plugin_instances:
            return {"status": "not_loaded", "healthy": False}
        
        plugin = self.plugin_instances[plugin_name]
        metadata = plugin.get_metadata()
        
        return {
            "status": "loaded",
            "healthy": True,
            "metadata": metadata,
            "vram_usage_gb": plugin.get_vram_usage()
        }
    
    def get_all_plugin_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all plugins.
        
        Returns:
            Dictionary mapping plugin names to health status
        """
        return {
            name: self.get_plugin_health(name)
            for name in self.loaded_plugins.keys()
        }
