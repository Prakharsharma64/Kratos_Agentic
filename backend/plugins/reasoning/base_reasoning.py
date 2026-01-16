"""Base reasoning plugin interface."""

from typing import Any, Dict, List
from ...core.plugin_base import PluginBase, PluginType


class BaseReasoningPlugin(PluginBase):
    """Base class for reasoning plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        """Reasoning plugin type."""
        return PluginType.REASONING
    
    @property
    def dependencies(self) -> List[str]:
        """No dependencies by default."""
        return []
    
    async def process(self, *args, **kwargs) -> str:
        """Perform reasoning.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Reasoning result text
        """
        raise NotImplementedError("Subclasses must implement process method")
