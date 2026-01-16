"""Base plugin interface for all plugins in the system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from enum import Enum


class PluginType(Enum):
    """Plugin category types."""
    INPUT = "input"
    COGNITIVE = "cognitive"
    REASONING = "reasoning"
    MEMORY = "memory"
    HUMANIZATION = "humanization"
    OUTPUT = "output"


class PluginBase(ABC):
    """Base class for all plugins in the system."""
    
    @property
    @abstractmethod
    def plugin_type(self) -> PluginType:
        """Plugin category."""
        pass
    
    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Unique plugin identifier."""
        pass
    
    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """Plugin version (semantic versioning)."""
        pass
    
    @property
    @abstractmethod
    def dependencies(self) -> List[str]:
        """List of required plugin names."""
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin with configuration.
        
        Args:
            config: Plugin-specific configuration dictionary
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        pass
    
    @abstractmethod
    async def process(self, *args, **kwargs) -> Any:
        """Main processing method.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Processing result (type depends on plugin)
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return plugin metadata.
        
        Returns:
            Dictionary containing plugin metadata
        """
        return {
            "type": self.plugin_type.value,
            "name": self.plugin_name,
            "version": self.plugin_version,
            "dependencies": self.dependencies
        }
    
    def get_vram_usage(self) -> float:
        """Get current VRAM usage in GB.
        
        Returns:
            VRAM usage in gigabytes (0.0 if not applicable)
        """
        return 0.0
