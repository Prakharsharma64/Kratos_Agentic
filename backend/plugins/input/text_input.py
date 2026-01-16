"""Text input processing plugin."""

import re
import logging
from typing import Any, Dict, List

from .base_input import BaseInputPlugin

logger = logging.getLogger(__name__)


class TextInputPlugin(BaseInputPlugin):
    """Text normalization and preprocessing plugin."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "text_input"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        logger.info("Text input plugin initialized")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        logger.info("Text input plugin cleaned up")
    
    async def process(self, content: Any, **kwargs) -> str:
        """Normalize and preprocess text input.
        
        Args:
            content: Input text
            **kwargs: Additional options
            
        Returns:
            Normalized text
        """
        if not isinstance(content, str):
            content = str(content)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', content.strip())
        
        # Normalize emoji (keep but ensure proper spacing)
        text = re.sub(r'([\U0001F300-\U0001F9FF])', r' \1 ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize common slang/abbreviations
        slang_map = {
            r'\bu\b': 'you',
            r'\bur\b': 'your',
            r'\bthru\b': 'through',
            r'\bthx\b': 'thanks',
            r'\bplz\b': 'please',
            r'\br\b': 'are',
            r'\bu\b': 'you',
            r'\b2\b': 'to',
            r'\b4\b': 'for',
            r'\b@\b': 'at',
            r'\b&\b': 'and',
        }
        
        for pattern, replacement in slang_map.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Remove excessive punctuation (keep single instances)
        text = re.sub(r'([!?.]){2,}', r'\1', text)
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace("'", "'").replace("'", "'")
        
        return text.strip()
