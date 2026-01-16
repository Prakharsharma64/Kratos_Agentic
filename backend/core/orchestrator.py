"""Main request orchestrator."""

import logging
from typing import Dict, Any, Optional, AsyncIterator
from enum import Enum

from .plugin_manager import PluginManager
from .plugin_base import PluginType
from .config import get_config

logger = logging.getLogger(__name__)


class RequestType(Enum):
    """Request type enumeration."""
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"


class Orchestrator:
    """Orchestrates request processing through plugins."""
    
    def __init__(self, plugin_manager: PluginManager):
        """Initialize orchestrator.
        
        Args:
            plugin_manager: Plugin manager instance
        """
        self.plugin_manager = plugin_manager
        self.config = get_config()
    
    async def process_request(
        self,
        request_type: RequestType,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Process a request through the plugin pipeline.
        
        Args:
            request_type: Type of request
            content: Request content (text, audio bytes, image, etc.)
            metadata: Optional request metadata
            
        Yields:
            Processing results as dictionaries
        """
        if metadata is None:
            metadata = {}
        
        # Step 1: Input processing
        input_text = await self._process_input(request_type, content)
        
        # Step 2: Intent classification
        intent_result = await self._classify_intent(input_text)
        
        # Step 3: Complexity detection
        complexity_result = await self._detect_complexity(input_text, intent_result)
        
        # Step 4: Entity extraction
        entities = await self._extract_entities(input_text)
        
        # Step 5: Reasoning (single agent or council)
        reasoning_result = await self._reason(
            input_text,
            intent_result,
            complexity_result,
            entities
        )
        
        # Step 6: Humanization
        humanized_text = await self._humanize(reasoning_result)
        
        # Step 7: Memory storage
        await self._store_memory(input_text, humanized_text, metadata)
        
        # Step 8: Output generation
        async for output_chunk in self._generate_output(humanized_text, request_type):
            yield output_chunk
    
    async def _process_input(self, request_type: RequestType, content: Any) -> str:
        """Process input based on type.
        
        Args:
            request_type: Request type
            content: Input content
            
        Returns:
            Processed text
        """
        input_plugins = await self.plugin_manager.get_plugins_by_type(PluginType.INPUT)
        
        for plugin in input_plugins:
            # Match plugin to request type
            plugin_name = plugin.plugin_name
            if request_type == RequestType.TEXT and "text" in plugin_name:
                result = await plugin.process(content)
                return result if isinstance(result, str) else str(result)
            elif request_type == RequestType.AUDIO and "audio" in plugin_name:
                result = await plugin.process(content)
                return result if isinstance(result, str) else str(result)
            elif request_type == RequestType.IMAGE and "image" in plugin_name:
                result = await plugin.process(content)
                return result if isinstance(result, str) else str(result)
            elif request_type == RequestType.VIDEO and "video" in plugin_name:
                result = await plugin.process(content)
                return result if isinstance(result, str) else str(result)
        
        # Fallback: treat as text
        if isinstance(content, str):
            return content
        return str(content)
    
    async def _classify_intent(self, text: str) -> Dict[str, Any]:
        """Classify user intent.
        
        Args:
            text: Input text
            
        Returns:
            Intent classification result
        """
        intent_plugin = await self.plugin_manager.get_plugin("intent_classifier")
        if intent_plugin:
            return await intent_plugin.process(text)
        return {"intent": "unknown", "confidence": 0.0}
    
    async def _detect_complexity(self, text: str, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """Detect query complexity.
        
        Args:
            text: Input text
            intent_result: Intent classification result
            
        Returns:
            Complexity detection result
        """
        complexity_plugin = await self.plugin_manager.get_plugin("complexity_detector")
        if complexity_plugin:
            return await complexity_plugin.process(text, intent_result)
        return {"complexity": 0.5, "score": 0.5}
    
    async def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text.
        
        Args:
            text: Input text
            
        Returns:
            Entity extraction result
        """
        entity_plugin = await self.plugin_manager.get_plugin("entity_extractor")
        if entity_plugin:
            return await entity_plugin.process(text)
        return {"entities": []}
    
    async def _reason(
        self,
        text: str,
        intent: Dict[str, Any],
        complexity: Dict[str, Any],
        entities: Dict[str, Any]
    ) -> str:
        """Perform reasoning (single agent or council).
        
        Args:
            text: Input text
            intent: Intent classification
            complexity: Complexity detection
            entities: Extracted entities
            
        Returns:
            Reasoning result text
        """
        complexity_score = complexity.get("score", 0.5)
        
        # Determine if council is needed
        if complexity_score < self.config.council.simple_threshold:
            # Simple query - single agent
            phi_plugin = await self.plugin_manager.get_plugin("phi_reasoner")
            if phi_plugin:
                result = await phi_plugin.process(text, intent, entities)
                return result if isinstance(result, str) else str(result)
        else:
            # Complex query - use council
            council_plugin = await self.plugin_manager.get_plugin("council_coordinator")
            if council_plugin:
                # Determine council size
                if complexity_score < self.config.council.medium_threshold:
                    council_size = 4
                else:
                    council_size = 8
                
                result = await council_plugin.process(text, intent, entities, council_size)
                return result if isinstance(result, str) else str(result)
        
        # Fallback
        return "I'm processing your request."
    
    async def _humanize(self, text: str) -> str:
        """Humanize the response.
        
        Args:
            text: Response text
            
        Returns:
            Humanized text
        """
        humanizer_plugin = await self.plugin_manager.get_plugin("phi_humanizer")
        if humanizer_plugin:
            result = await humanizer_plugin.process(text)
            return result if isinstance(result, str) else str(result)
        return text
    
    async def _store_memory(self, input_text: str, output_text: str, metadata: Dict[str, Any]) -> None:
        """Store interaction in memory.
        
        Args:
            input_text: User input
            output_text: System response
            metadata: Request metadata
        """
        memory_plugin = await self.plugin_manager.get_plugin("vector_memory")
        if memory_plugin:
            await memory_plugin.process(input_text, output_text, metadata)
    
    async def _generate_output(self, text: str, request_type: RequestType) -> AsyncIterator[Dict[str, Any]]:
        """Generate output (text or audio).
        
        Args:
            text: Response text
            request_type: Original request type
            
        Yields:
            Output chunks
        """
        # Text output
        text_output_plugin = await self.plugin_manager.get_plugin("text_output")
        if text_output_plugin:
            async for chunk in text_output_plugin.process(text):
                yield {"type": "text", "content": chunk}
        
        # Audio output if original was audio
        if request_type == RequestType.AUDIO:
            audio_output_plugin = await self.plugin_manager.get_plugin("audio_output")
            if audio_output_plugin:
                async for chunk in audio_output_plugin.process(text):
                    yield {"type": "audio", "content": chunk}
