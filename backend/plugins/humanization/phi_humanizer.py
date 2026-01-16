"""Phi-based humanization plugin."""

import logging
import re
from typing import Any, Dict, List

from .base_humanizer import BaseHumanizerPlugin
from ...core.config import get_config

logger = logging.getLogger(__name__)


class PhiHumanizerPlugin(BaseHumanizerPlugin):
    """Humanization using Phi-3.5-mini style matching."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "phi_humanizer"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def dependencies(self) -> List[str]:
        """Dependencies."""
        return ["phi_reasoner"]
    
    def __init__(self):
        """Initialize plugin."""
        self.config = get_config()
        self.phi_plugin = None
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        logger.info("Phi humanizer plugin initialized")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        logger.info("Phi humanizer plugin cleaned up")
    
    async def process(self, text: str, **kwargs) -> str:
        """Humanize text with style matching.
        
        Args:
            text: Input text
            **kwargs: Additional options (confidence, domain, etc.)
            
        Returns:
            Humanized text
        """
        # Check domain exclusions
        domain = kwargs.get("domain", self._detect_domain(text))
        if domain in self.config.humanization.exclude_domains:
            logger.debug(f"Skipping humanization for domain: {domain}")
            return text
        
        # Get Phi plugin
        if self.phi_plugin is None:
            self.phi_plugin = getattr(self, "phi_reasoner_plugin", None)
        
        # Simple humanization (can be enhanced with Phi)
        humanized = text
        
        # Clamp emoji usage
        humanized = self._clamp_emoji(humanized)
        
        # Add warmth (simple heuristics)
        humanized = self._add_warmth(humanized)
        
        # If Phi available, use it for style matching
        if self.phi_plugin:
            try:
                confidence = kwargs.get("confidence", 0.7)
                if confidence > 0.6:
                    # Use Phi for style matching
                    style_prompt = f"Make this response more conversational and warm, but keep the same meaning:\n\n{text}\n\nHumanized:"
                    phi_response = await self.phi_plugin.process(style_prompt)
                    if phi_response and len(phi_response) > 10:
                        humanized = phi_response
            except Exception as e:
                logger.warning(f"Phi humanization failed: {e}, using fallback")
        
        return humanized
    
    def _detect_domain(self, text: str) -> str:
        """Detect text domain."""
        text_lower = text.lower()
        
        # Legal
        legal_keywords = ["legal", "law", "attorney", "lawsuit", "contract", "liability"]
        if any(keyword in text_lower for keyword in legal_keywords):
            return "legal"
        
        # Medical
        medical_keywords = ["medical", "diagnosis", "treatment", "symptom", "disease", "patient"]
        if any(keyword in text_lower for keyword in medical_keywords):
            return "medical"
        
        # SQL
        sql_keywords = ["select", "from", "where", "sql", "query", "database"]
        if any(keyword in text_lower for keyword in sql_keywords):
            return "sql"
        
        return "general"
    
    def _clamp_emoji(self, text: str) -> str:
        """Clamp emoji usage per message."""
        max_emoji = self.config.humanization.emoji_max_per_message
        
        # Count emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        
        emojis = emoji_pattern.findall(text)
        if len(emojis) > max_emoji:
            # Remove excess emojis
            for i, emoji in enumerate(emojis):
                if i >= max_emoji:
                    text = text.replace(emoji, "", 1)
        
        return text
    
    def _add_warmth(self, text: str) -> str:
        """Add warmth to text (simple heuristics)."""
        # Don't modify if too technical
        if len(text.split()) < 5:
            return text
        
        # Add friendly transitions
        if text.startswith("The") and not text.startswith("The user"):
            text = text.replace("The", "Here's", 1)
        
        # Ensure proper punctuation
        if not text.endswith((".", "!", "?")):
            text += "."
        
        return text
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        return 0.0  # Uses Phi plugin's VRAM
