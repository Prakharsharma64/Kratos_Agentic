"""Base cognitive plugin interface."""

from typing import Any, Dict, List
from ...core.plugin_base import PluginBase, PluginType


class BaseCognitivePlugin(PluginBase):
    """Base class for cognitive processing plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        """Cognitive plugin type."""
        return PluginType.COGNITIVE
    
    @property
    def dependencies(self) -> List[str]:
        """No dependencies by default."""
        return []
    
    async def process(self, *args, **kwargs) -> Any:
        """Process cognitive task.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Processing result
        """
        raise NotImplementedError("Subclasses must implement process method")
