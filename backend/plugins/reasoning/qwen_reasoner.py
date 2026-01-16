"""Qwen2.5-7B reasoning plugin (on-demand)."""

import logging
import asyncio
from typing import Any, Dict, List

from .base_reasoning import BaseReasoningPlugin
from ...core.model_manager import ModelManager
from ...core.vram_monitor import ModelPriority

logger = logging.getLogger(__name__)


class QwenReasonerPlugin(BaseReasoningPlugin):
    """Heavy reasoning using Qwen2.5-7B (on-demand only)."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "qwen_reasoner"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    def __init__(self):
        """Initialize plugin."""
        self.model_manager: ModelManager = None
        self.model = None
        self.tokenizer = None
        self._loaded = False
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin (but don't load model yet)."""
        from ...core.model_manager import ModelManager
        from ...core.vram_monitor import VRAMMonitor
        
        # Get model manager
        if hasattr(self, 'model_manager_plugin'):
            self.model_manager = self.model_manager_plugin
        else:
            vram_monitor = VRAMMonitor()
            self.model_manager = ModelManager(vram_monitor)
        
        # Don't load model yet - load on demand
        logger.info("Qwen reasoner plugin initialized (model will load on demand)")
    
    async def _ensure_loaded(self) -> None:
        """Ensure model is loaded."""
        if self._loaded and self.model is not None:
            return
        
        # Load Qwen2.5-7B
        model_name = "Qwen/Qwen2.5-7B-Instruct"
        self.model, self.tokenizer = await self.model_manager.load_model(
            model_name,
            model_type="causal_lm",
            priority=ModelPriority.HIGH  # High priority but can be evicted
        )
        self._loaded = True
        logger.info("Qwen model loaded")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        if self.model_manager and self.model:
            await self.model_manager.unload_model("Qwen/Qwen2.5-7B-Instruct")
            self._loaded = False
        logger.info("Qwen reasoner plugin cleaned up")
    
    async def process(self, text: str, context: Dict[str, Any] = None, **kwargs) -> str:
        """Perform heavy reasoning/synthesis.
        
        Args:
            text: Input text or synthesis context
            context: Additional context (council opinions, etc.)
            **kwargs: Additional options
            
        Returns:
            Synthesized response
        """
        # Ensure model is loaded
        await self._ensure_loaded()
        
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded")
        
        # Build prompt for synthesis
        prompt = self._build_synthesis_prompt(text, context)
        
        # Generate
        max_tokens = kwargs.get("max_tokens", 1024)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self._generate_sync,
            prompt,
            max_tokens
        )
        
        return response
    
    def _build_synthesis_prompt(self, text: str, context: Dict[str, Any] = None) -> str:
        """Build synthesis prompt."""
        if context and "opinions" in context:
            # Council synthesis
            prompt = "Synthesize the following opinions into a coherent response:\n\n"
            for i, opinion in enumerate(context["opinions"], 1):
                prompt += f"Opinion {i}: {opinion}\n\n"
            prompt += "Synthesized response:"
        else:
            # Regular reasoning
            prompt = f"User: {text}\n\nAssistant:"
        return prompt
    
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
        
        # Remove prompt
        if "Assistant:" in response:
            response = response.split("Assistant:")[-1].strip()
        elif "Synthesized response:" in response:
            response = response.split("Synthesized response:")[-1].strip()
        
        return response
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        return 14.0 if self._loaded else 0.0
