"""Entity extraction plugin using GLiNER."""

import logging
import asyncio
from typing import Any, Dict, List

from .base_cognitive import BaseCognitivePlugin
from ...core.model_manager import ModelManager
from ...core.vram_monitor import ModelPriority

logger = logging.getLogger(__name__)


class EntityExtractorPlugin(BaseCognitivePlugin):
    """Entity extraction using GLiNER."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "entity_extractor"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    def __init__(self):
        """Initialize plugin."""
        self.model_manager: ModelManager = None
        self.model = None
    
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
        
        # Load GLiNER model
        try:
            model_name = "urchade/gliner_small-v2.1"
            self.model, _ = await self.model_manager.load_model(
                model_name,
                model_type="base",
                priority=ModelPriority.MEDIUM
            )
            logger.info("Entity extractor plugin initialized")
        except Exception as e:
            logger.warning(f"Failed to load GLiNER model: {e}. Using fallback.")
            self.model = None
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        if self.model_manager and self.model:
            await self.model_manager.unload_model("urchade/gliner_small-v2.1")
        logger.info("Entity extractor plugin cleaned up")
    
    async def process(self, text: str, **kwargs) -> Dict[str, Any]:
        """Extract entities from text.
        
        Args:
            text: Input text
            **kwargs: Additional options (entity_types, etc.)
            
        Returns:
            Entity extraction result
        """
        # Default entity types
        entity_types = kwargs.get("entity_types", [
            "person", "location", "organization", "date", "time", "money", "product"
        ])
        
        if self.model is None:
            # Fallback: simple regex-based extraction
            return self._extract_entities_fallback(text, entity_types)
        
        # Use GLiNER for extraction
        try:
            loop = asyncio.get_event_loop()
            entities = await loop.run_in_executor(
                None,
                self._extract_with_gliner,
                text,
                entity_types
            )
            return {"entities": entities}
        except Exception as e:
            logger.warning(f"GLiNER extraction failed: {e}. Using fallback.")
            return self._extract_entities_fallback(text, entity_types)
    
    def _extract_with_gliner(self, text: str, entity_types: List[str]) -> List[Dict[str, Any]]:
        """Extract entities using GLiNER synchronously."""
        try:
            from gliner import GLiNER
            
            # Initialize GLiNER if not already done
            if not hasattr(self, '_gliner_instance'):
                self._gliner_instance = GLiNER.from_pretrained("urchade/gliner_small-v2.1")
            
            # Extract entities
            entities = self._gliner_instance.predict_entities(text, entity_types, threshold=0.5)
            
            # Format results
            return [
                {
                    "text": ent["text"],
                    "label": ent["label"],
                    "start": ent.get("start", 0),
                    "end": ent.get("end", 0),
                    "score": ent.get("score", 1.0)
                }
                for ent in entities
            ]
        except ImportError:
            logger.error("GLiNER not installed. Install with: pip install gliner")
            return []
    
    def _extract_entities_fallback(self, text: str, entity_types: List[str]) -> List[Dict[str, Any]]:
        """Fallback entity extraction using simple patterns."""
        entities = []
        
        # Simple patterns (can be enhanced)
        patterns = {
            "person": r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # First Last
            "location": r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b',  # Place names
            "date": r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            "time": r'\b(\d{1,2}:\d{2}(?:\s?[AP]M)?)\b',
            "money": r'\$(\d+(?:\.\d{2})?)',
        }
        
        for entity_type in entity_types:
            if entity_type in patterns:
                import re
                matches = re.finditer(patterns[entity_type], text)
                for match in matches:
                    entities.append({
                        "text": match.group(1),
                        "label": entity_type,
                        "start": match.start(),
                        "end": match.end(),
                        "score": 0.6
                    })
        
        return entities
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        return 0.2
