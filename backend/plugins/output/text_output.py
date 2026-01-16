"""Text output streaming plugin."""

import logging
from typing import Any, Dict, List, AsyncIterator

from .base_output import BaseOutputPlugin

logger = logging.getLogger(__name__)


class TextOutputPlugin(BaseOutputPlugin):
    """Text streaming output plugin."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "text_output"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        logger.info("Text output plugin initialized")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        logger.info("Text output plugin cleaned up")
    
    async def process(self, content: str, **kwargs) -> AsyncIterator[str]:
        """Stream text output.
        
        Args:
            content: Text content to stream
            **kwargs: Additional options (chunk_size, format, etc.)
            
        Yields:
            Text chunks
        """
        chunk_size = kwargs.get("chunk_size", 10)  # Words per chunk
        
        words = content.split()
        
        # Stream in chunks
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
            yield chunk
        
        # Format as markdown if requested
        if kwargs.get("format_markdown", False):
            # Simple markdown formatting (can be enhanced)
            formatted = self._format_markdown(content)
            yield formatted
    
    def _format_markdown(self, text: str) -> str:
        """Format text as markdown."""
        # Simple markdown formatting
        # In production, would use a proper markdown library
        lines = text.split("\n")
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue
            
            # Headers
            if line.startswith("#"):
                formatted_lines.append(line)
            # Lists
            elif line.startswith("-") or line.startswith("*"):
                formatted_lines.append(line)
            # Code blocks
            elif "`" in line:
                formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        return "\n".join(formatted_lines)
