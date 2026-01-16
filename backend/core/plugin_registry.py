"""Plugin discovery and registration system."""

import logging
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import yaml

from .plugin_base import PluginBase, PluginType

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Manages plugin discovery and registration."""
    
    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        """Initialize plugin registry.
        
        Args:
            plugin_dirs: List of directories to search for plugins
        """
        if plugin_dirs is None:
            # Default plugin directories
            base_dir = Path(__file__).parent.parent
            plugin_dirs = [
                base_dir / "plugins",  # Built-in plugins
                base_dir.parent / "plugins"  # External plugins
            ]
        
        self.plugin_dirs = [Path(d) for d in plugin_dirs]
        self.plugin_classes: Dict[str, Type[PluginBase]] = {}
        self.plugin_metadata: Dict[str, Dict[str, Any]] = {}
    
    def discover_plugins(self) -> Dict[str, Type[PluginBase]]:
        """Discover all plugins in plugin directories.
        
        Returns:
            Dictionary mapping plugin names to plugin classes
        """
        discovered = {}
        
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                logger.debug(f"Plugin directory does not exist: {plugin_dir}")
                continue
            
            # Discover plugins in subdirectories
            for plugin_path in plugin_dir.iterdir():
                if not plugin_path.is_dir():
                    continue
                
                # Skip __pycache__ and hidden directories
                if plugin_path.name.startswith("_") or plugin_path.name.startswith("."):
                    continue
                
                # Try to load plugin
                plugin_class = self._load_plugin_from_directory(plugin_path)
                if plugin_class:
                    plugin_name = plugin_class.plugin_name
                    discovered[plugin_name] = plugin_class
                    logger.info(f"Discovered plugin: {plugin_name} from {plugin_path}")
        
        self.plugin_classes.update(discovered)
        return discovered
    
    def _load_plugin_from_directory(self, plugin_dir: Path) -> Optional[Type[PluginBase]]:
        """Load a plugin from a directory.
        
        Args:
            plugin_dir: Plugin directory path
            
        Returns:
            Plugin class or None
        """
        # Look for plugin.yaml
        plugin_yaml = plugin_dir / "plugin.yaml"
        metadata = {}
        
        if plugin_yaml.exists():
            try:
                with open(plugin_yaml, 'r') as f:
                    metadata = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to load plugin.yaml from {plugin_dir}: {e}")
        
        # Look for Python files
        plugin_files = list(plugin_dir.glob("*.py"))
        if not plugin_files:
            return None
        
        # Try to import the plugin
        for plugin_file in plugin_files:
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                # Construct module path
                # Assuming plugin_dir is backend/plugins/input/text_input.py
                # We need to import backend.plugins.input.text_input
                relative_path = plugin_file.relative_to(Path(__file__).parent.parent)
                module_parts = relative_path.with_suffix("").parts
                module_name = ".".join(module_parts)
                
                # Import module
                module = importlib.import_module(module_name)
                
                # Find PluginBase subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, PluginBase) and 
                        obj is not PluginBase and
                        obj.__module__ == module_name):
                        # Store metadata
                        self.plugin_metadata[obj.plugin_name] = {
                            **metadata,
                            "module": module_name,
                            "file": str(plugin_file)
                        }
                        return obj
                        
            except Exception as e:
                logger.warning(f"Failed to import plugin from {plugin_file}: {e}")
                continue
        
        return None
    
    def register_plugin(self, plugin_class: Type[PluginBase]) -> None:
        """Manually register a plugin class.
        
        Args:
            plugin_class: Plugin class to register
        """
        if not issubclass(plugin_class, PluginBase):
            raise ValueError(f"{plugin_class} is not a PluginBase subclass")
        
        plugin_name = plugin_class.plugin_name
        self.plugin_classes[plugin_name] = plugin_class
        logger.info(f"Registered plugin: {plugin_name}")
    
    def get_plugin_class(self, plugin_name: str) -> Optional[Type[PluginBase]]:
        """Get a plugin class by name.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Plugin class or None
        """
        return self.plugin_classes.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, Type[PluginBase]]:
        """Get all registered plugins.
        
        Returns:
            Dictionary of plugin names to classes
        """
        return self.plugin_classes.copy()
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a plugin.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Plugin metadata dictionary or None
        """
        return self.plugin_metadata.get(plugin_name)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[str]:
        """Get all plugin names of a specific type.
        
        Args:
            plugin_type: Plugin type
            
        Returns:
            List of plugin names
        """
        return [
            name for name, cls in self.plugin_classes.items()
            if cls.plugin_type == plugin_type
        ]
