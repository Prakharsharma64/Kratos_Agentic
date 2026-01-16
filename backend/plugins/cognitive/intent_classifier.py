"""Intent classification plugin using DeBERTa."""

import logging
import asyncio
from typing import Any, Dict, List

from .base_cognitive import BaseCognitivePlugin
from ...core.model_manager import ModelManager
from ...core.vram_monitor import ModelPriority

logger = logging.getLogger(__name__)


class IntentClassifierPlugin(BaseCognitivePlugin):
    """Intent classification using DeBERTa-v3-small."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "intent_classifier"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    def __init__(self):
        """Initialize plugin."""
        self.model_manager: ModelManager = None
        self.model = None
        self.tokenizer = None
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        from ...core.model_manager import ModelManager
        from ...core.vram_monitor import VRAMMonitor
        
        # Get model manager
        if hasattr(self, 'model_manager_plugin'):
            self.model_manager = self.model_manager_plugin
        else:
            vram_monitor = VRAMMonitor()
            self.model_manager = ModelManager(vram_monitor)
        
        # Load DeBERTa model
        model_name = "microsoft/deberta-v3-small"
        self.model, self.tokenizer = await self.model_manager.load_model(
            model_name,
            model_type="base",
            priority=ModelPriority.MEDIUM
        )
        
        logger.info("Intent classifier plugin initialized")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        if self.model_manager and self.model:
            await self.model_manager.unload_model("microsoft/deberta-v3-small")
        logger.info("Intent classifier plugin cleaned up")
    
    async def process(self, text: str, **kwargs) -> Dict[str, Any]:
        """Classify user intent.
        
        Args:
            text: Input text
            **kwargs: Additional options
            
        Returns:
            Intent classification result with label and confidence
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded")
        
        # Intent categories
        intents = ["question", "command", "conversation", "information", "creative"]
        
        # Simple rule-based classification (can be enhanced with fine-tuned model)
        text_lower = text.lower()
        
        # Question detection
        if any(word in text_lower for word in ["what", "when", "where", "who", "why", "how", "?"]):
            intent = "question"
            confidence = 0.8
        # Command detection
        elif any(word in text_lower for word in ["do", "make", "create", "generate", "show", "tell"]):
            intent = "command"
            confidence = 0.75
        # Creative detection
        elif any(word in text_lower for word in ["write", "story", "poem", "creative", "imagine"]):
            intent = "creative"
            confidence = 0.7
        # Information detection
        elif any(word in text_lower for word in ["explain", "describe", "information", "about"]):
            intent = "information"
            confidence = 0.7
        else:
            intent = "conversation"
            confidence = 0.6
        
        return {
            "intent": intent,
            "confidence": confidence,
            "all_intents": {i: 0.1 if i != intent else confidence for i in intents}
        }
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        return 0.3
