"""Base input plugin interface."""

from typing import Any, Dict, List
from ...core.plugin_base import PluginBase, PluginType


class BaseInputPlugin(PluginBase):
    """Base class for input processing plugins."""
    
    @property
    def plugin_type(self) -> PluginType:
        """Input plugin type."""
        return PluginType.INPUT
    
    @property
    def dependencies(self) -> List[str]:
        """No dependencies by default."""
        return []
    
    async def process(self, content: Any, **kwargs) -> str:
        """Process input content and return text.
        
        Args:
            content: Input content (text, audio bytes, image, etc.)
            **kwargs: Additional processing options
            
        Returns:
            Processed text
        """
        raise NotImplementedError("Subclasses must implement process method")
