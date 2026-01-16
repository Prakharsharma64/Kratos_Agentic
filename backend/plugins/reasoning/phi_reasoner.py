"""Phi-3.5-mini reasoning plugin (always loaded)."""

import logging
import asyncio
from typing import Any, Dict, List, AsyncIterator

from .base_reasoning import BaseReasoningPlugin
from ...core.model_manager import ModelManager
from ...core.vram_monitor import ModelPriority

logger = logging.getLogger(__name__)


class PhiReasonerPlugin(BaseReasoningPlugin):
    """Fast reasoning using Phi-3.5-mini (always loaded)."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "phi_reasoner"
    
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
        
        # Load Phi-3.5-mini (always loaded, critical priority)
        model_name = "microsoft/phi-3.5-mini-instruct"
        self.model, self.tokenizer = await self.model_manager.load_model(
            model_name,
            model_type="causal_lm",
            priority=ModelPriority.CRITICAL  # Never evict
        )
        
        logger.info("Phi reasoner plugin initialized (always loaded)")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        # Note: Phi model should stay loaded, but we'll unload if needed
        if self.model_manager and self.model:
            await self.model_manager.unload_model("microsoft/phi-3.5-mini-instruct")
        logger.info("Phi reasoner plugin cleaned up")
    
    async def process(self, text: str, intent: Dict[str, Any] = None, entities: Dict[str, Any] = None, **kwargs) -> str:
        """Generate response using Phi-3.5-mini.
        
        Args:
            text: Input text
            intent: Intent classification result
            entities: Extracted entities
            **kwargs: Additional options (stream, max_tokens, etc.)
            
        Returns:
            Generated response text
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded")
        
        # Build prompt
        prompt = self._build_prompt(text, intent, entities)
        
        # Generate
        stream = kwargs.get("stream", False)
        max_tokens = kwargs.get("max_tokens", 512)
        
        if stream:
            # Streaming generation
            async for token in self._generate_stream(prompt, max_tokens):
                yield token
        else:
            # Non-streaming generation
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._generate_sync,
                prompt,
                max_tokens
            )
            return response
    
    def _build_prompt(self, text: str, intent: Dict[str, Any] = None, entities: Dict[str, Any] = None) -> str:
        """Build prompt for Phi model."""
        prompt = f"User: {text}\n\nAssistant:"
        return prompt
    
    async def _generate_stream(self, prompt: str, max_tokens: int) -> AsyncIterator[str]:
        """Generate response with streaming."""
        loop = asyncio.get_event_loop()
        
        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt")
        if hasattr(self.model, "device"):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        # Generate with streaming
        generated_text = ""
        with self.model.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                streamer=None  # Would use TextIteratorStreamer for real streaming
            )
        
        # Decode and yield tokens (simplified - real streaming would use streamer)
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Remove prompt from response
        if "Assistant:" in response:
            response = response.split("Assistant:")[-1].strip()
        
        # Yield in chunks (simplified)
        words = response.split()
        for word in words:
            yield word + " "
    
    def _generate_sync(self, prompt: str, max_tokens: int) -> str:
        """Generate response synchronously."""
        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt")
        if hasattr(self.model, "device"):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        # Generate
        with self.model.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9
            )
        
        # Decode
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove prompt from response
        if "Assistant:" in response:
            response = response.split("Assistant:")[-1].strip()
        
        return response
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        return 2.0
