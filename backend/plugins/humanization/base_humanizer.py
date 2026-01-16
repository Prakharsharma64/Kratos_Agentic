"""Base humanization plugin interface."""

from typing import Any, Dict, List
from ...core.plugin_base import PluginBase, PluginType


class BaseHumanizerPlugin(PluginBase):
    """Base class for humanization plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        """Humanization plugin type."""
        return PluginType.HUMANIZATION
    
    @property
    def dependencies(self) -> List[str]:
        """No dependencies by default."""
        return []
    
    async def process(self, text: str, **kwargs) -> str:
        """Humanize text.
        
        Args:
            text: Input text
            **kwargs: Additional options
            
        Returns:
            Humanized text
        """
        raise NotImplementedError("Subclasses must implement process method")
