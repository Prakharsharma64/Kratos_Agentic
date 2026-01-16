"""Memory confidence decay plugin."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from .base_memory import BaseMemoryPlugin

logger = logging.getLogger(__name__)


class ConfidenceDecayPlugin(BaseMemoryPlugin):
    """Automatic memory confidence decay."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "confidence_decay"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def dependencies(self) -> List[str]:
        """Dependencies."""
        return ["vector_memory"]
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        from ...core.config import get_config
        self.config = get_config()
        logger.info("Confidence decay plugin initialized")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        logger.info("Confidence decay plugin cleaned up")
    
    async def process(self, memory_entry: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Apply decay to memory confidence.
        
        Args:
            memory_entry: Memory entry to decay
            **kwargs: Additional options
            
        Returns:
            Updated memory entry with decayed confidence
        """
        if memory_entry is None:
            # Batch decay operation
            return await self._batch_decay()
        
        # Single memory decay
        return self._decay_single(memory_entry)
    
    def _decay_single(self, memory_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Apply decay to a single memory entry."""
        payload = memory_entry.get("payload", {})
        confidence = payload.get("confidence", 0.5)
        last_verified = payload.get("last_verified")
        decay_rate = payload.get("decay_rate", self.config.memory.decay_rate)
        
        if not last_verified:
            return memory_entry
        
        # Calculate time since last verification
        try:
            last_verified_dt = datetime.fromisoformat(last_verified)
            days_since = (datetime.now() - last_verified_dt).days
        except:
            days_since = 0
        
        # Apply exponential decay
        new_confidence = confidence * (1 - decay_rate) ** days_since
        
        # Update entry
        memory_entry["payload"]["confidence"] = max(0.0, new_confidence)
        
        return memory_entry
    
    async def _batch_decay(self) -> Dict[str, Any]:
        """Apply decay to all memories (background task)."""
        # Get memory plugin
        memory_plugin = getattr(self, "vector_memory_plugin", None)
        if memory_plugin is None:
            return {"processed": 0, "removed": 0}
        
        # This would typically iterate through all memories
        # For now, return summary
        return {
            "processed": 0,
            "removed": 0,
            "message": "Batch decay not fully implemented (requires memory iteration)"
        }
    
    def should_remove(self, memory_entry: Dict[str, Any]) -> bool:
        """Check if memory should be removed (low confidence).
        
        Args:
            memory_entry: Memory entry
            
        Returns:
            True if should be removed
        """
        payload = memory_entry.get("payload", {})
        confidence = payload.get("confidence", 0.5)
        return confidence < self.config.memory.cleanup_threshold
    
    def should_deprioritize(self, memory_entry: Dict[str, Any]) -> bool:
        """Check if memory should be deprioritized.
        
        Args:
            memory_entry: Memory entry
            
        Returns:
            True if should be deprioritized
        """
        payload = memory_entry.get("payload", {})
        confidence = payload.get("confidence", 0.5)
        return confidence < self.config.memory.confidence_threshold
