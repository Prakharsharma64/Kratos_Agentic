"""Base output plugin interface."""

from typing import Any, Dict, List, AsyncIterator
from ...core.plugin_base import PluginBase, PluginType


class BaseOutputPlugin(PluginBase):
    """Base class for output plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        """Output plugin type."""
        return PluginType.OUTPUT
    
    @property
    def dependencies(self) -> List[str]:
        """No dependencies by default."""
        return []
    
    async def process(self, content: str, **kwargs) -> AsyncIterator[Any]:
        """Generate output.
        
        Args:
            content: Input content
            **kwargs: Additional options
            
        Yields:
            Output chunks
        """
        raise NotImplementedError("Subclasses must implement process method")
