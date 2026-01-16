"""Embedding generation plugin using BGE."""

import logging
import asyncio
import numpy as np
from typing import Any, Dict, List, Union

from .base_cognitive import BaseCognitivePlugin
from ...core.model_manager import ModelManager
from ...core.vram_monitor import ModelPriority

logger = logging.getLogger(__name__)


class EmbeddingAgentPlugin(BaseCognitivePlugin):
    """Text embedding generation using BGE."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "embedding_agent"
    
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
        
        # Load BGE model
        model_name = "BAAI/bge-small-en-v1.5"
        self.model, self.tokenizer = await self.model_manager.load_model(
            model_name,
            model_type="base",
            priority=ModelPriority.MEDIUM
        )
        
        logger.info("Embedding agent plugin initialized")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        if self.model_manager and self.model:
            await self.model_manager.unload_model("BAAI/bge-small-en-v1.5")
        logger.info("Embedding agent plugin cleaned up")
    
    async def process(self, text: Union[str, List[str]], **kwargs) -> Union[np.ndarray, List[np.ndarray]]:
        """Generate embeddings for text.
        
        Args:
            text: Input text or list of texts
            **kwargs: Additional options (normalize, etc.)
            
        Returns:
            Embedding vector(s) as numpy array(s)
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded")
        
        normalize = kwargs.get("normalize", True)
        is_batch = isinstance(text, list)
        
        if not is_batch:
            text = [text]
        
        # Generate embeddings
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self._generate_embeddings,
            text,
            normalize
        )
        
        if is_batch:
            return embeddings
        else:
            return embeddings[0]
    
    def _generate_embeddings(self, texts: List[str], normalize: bool) -> List[np.ndarray]:
        """Generate embeddings synchronously."""
        # Tokenize
        encoded_input = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        
        # Move to device
        if hasattr(self.model, "device"):
            encoded_input = {k: v.to(self.model.device) for k, v in encoded_input.items()}
        
        # Generate embeddings
        with self.model.no_grad():
            model_output = self.model(**encoded_input)
            embeddings = model_output.pooler_output if hasattr(model_output, "pooler_output") else model_output.last_hidden_state[:, 0]
        
        # Convert to numpy
        embeddings = embeddings.cpu().numpy()
        
        # Normalize
        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-8)
        
        return [emb for emb in embeddings]
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        return 0.13
