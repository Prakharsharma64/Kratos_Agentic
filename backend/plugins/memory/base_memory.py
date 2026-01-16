"""Base memory plugin interface."""

from typing import Any, Dict, List
from ...core.plugin_base import PluginBase, PluginType


class BaseMemoryPlugin(PluginBase):
    """Base class for memory plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        """Memory plugin type."""
        return PluginType.MEMORY
    
    @property
    def dependencies(self) -> List[str]:
        """No dependencies by default."""
        return []
    
    async def process(self, *args, **kwargs) -> Any:
        """Process memory operation.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Memory operation result
        """
        raise NotImplementedError("Subclasses must implement process method")
