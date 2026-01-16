"""VRAM-aware model loading and management."""

import logging
import asyncio
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
import torch
from transformers import AutoModel, AutoTokenizer, AutoModelForCausalLM
from transformers.utils import cached_file

from .vram_monitor import VRAMMonitor, ModelPriority, VRAMStatus
from .config import get_config

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages model loading, unloading, and VRAM allocation."""
    
    def __init__(self, vram_monitor: Optional[VRAMMonitor] = None):
        """Initialize model manager.
        
        Args:
            vram_monitor: VRAM monitor instance (creates new if None)
        """
        self.vram_monitor = vram_monitor or VRAMMonitor()
        self.config = get_config()
        self.loaded_models: Dict[str, Any] = {}
        self.model_metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
        # Update VRAM monitor limits from config
        self.vram_monitor.soft_limit = self.config.vram.soft_limit
        self.vram_monitor.hard_limit = self.config.vram.hard_limit
        
        # Ensure cache directory exists
        self.cache_dir = Path(self.config.models.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def load_model(
        self,
        model_name: str,
        model_type: str = "auto",
        priority: int = ModelPriority.MEDIUM,
        device: Optional[str] = None,
        **kwargs
    ) -> Tuple[Any, Any]:
        """Load a model asynchronously.
        
        Args:
            model_name: Hugging Face model identifier
            model_type: Model type ("auto", "causal_lm", "base", "tokenizer")
            priority: Eviction priority
            device: Device to load on (None = use config)
            **kwargs: Additional model loading arguments
            
        Returns:
            Tuple of (model, tokenizer) or (model, None)
        """
        async with self._lock:
            # Check if already loaded
            if model_name in self.loaded_models:
                logger.info(f"Model {model_name} already loaded")
                model_data = self.loaded_models[model_name]
                return model_data.get("model"), model_data.get("tokenizer")
            
            # Determine device
            if device is None:
                device = self.config.models.device
                if device == "cuda" and not torch.cuda.is_available():
                    device = "cpu"
                    logger.warning("CUDA not available, falling back to CPU")
            
            # Estimate VRAM usage (rough estimates)
            estimated_vram = self._estimate_vram_usage(model_name, model_type)
            
            # Check if we can load
            can_load, reason = self.vram_monitor.can_load_model(estimated_vram, priority)
            if not can_load:
                # Try to evict models
                if priority <= ModelPriority.HIGH:
                    models_to_evict = self.vram_monitor.get_models_to_evict(estimated_vram)
                    for model_id in models_to_evict:
                        await self.unload_model(model_id)
                    can_load, reason = self.vram_monitor.can_load_model(estimated_vram, priority)
            
            if not can_load:
                raise RuntimeError(f"Cannot load model {model_name}: {reason}")
            
            # Load model in executor to avoid blocking
            loop = asyncio.get_event_loop()
            model, tokenizer = await loop.run_in_executor(
                None,
                self._load_model_sync,
                model_name,
                model_type,
                device,
                **kwargs
            )
            
            # Register with VRAM monitor
            actual_vram = self._get_actual_vram_usage()
            self.vram_monitor.register_model(model_name, actual_vram, priority, device)
            
            # Store model
            self.loaded_models[model_name] = {
                "model": model,
                "tokenizer": tokenizer,
                "device": device,
                "priority": priority
            }
            
            logger.info(f"Loaded model {model_name} on {device} ({actual_vram:.2f} GB)")
            return model, tokenizer
    
    def _load_model_sync(
        self,
        model_name: str,
        model_type: str,
        device: str,
        **kwargs
    ) -> Tuple[Any, Optional[Any]]:
        """Synchronously load a model.
        
        Args:
            model_name: Hugging Face model identifier
            model_type: Model type
            device: Device to load on
            **kwargs: Additional arguments
            
        Returns:
            Tuple of (model, tokenizer)
        """
        try:
            # Load tokenizer
            tokenizer = None
            if model_type in ("auto", "causal_lm", "tokenizer"):
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir=str(self.cache_dir),
                    **kwargs
                )
            
            # Load model
            if model_type == "causal_lm":
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    cache_dir=str(self.cache_dir),
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                    device_map="auto" if device == "cuda" else None,
                    **kwargs
                )
            elif model_type == "base":
                model = AutoModel.from_pretrained(
                    model_name,
                    cache_dir=str(self.cache_dir),
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                    device_map="auto" if device == "cuda" else None,
                    **kwargs
                )
            else:
                # Auto-detect
                try:
                    model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        cache_dir=str(self.cache_dir),
                        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                        device_map="auto" if device == "cuda" else None,
                        **kwargs
                    )
                except:
                    model = AutoModel.from_pretrained(
                        model_name,
                        cache_dir=str(self.cache_dir),
                        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                        device_map="auto" if device == "cuda" else None,
                        **kwargs
                    )
            
            if device == "cuda" and not hasattr(model, "device"):
                model = model.to(device)
            
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            raise
    
    async def unload_model(self, model_name: str) -> None:
        """Unload a model and free VRAM.
        
        Args:
            model_name: Model identifier
        """
        async with self._lock:
            if model_name not in self.loaded_models:
                return
            
            model_data = self.loaded_models[model_name]
            model = model_data.get("model")
            
            # Move to CPU and delete
            if model is not None:
                if hasattr(model, "cpu"):
                    model.cpu()
                del model
            
            # Clear cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Unregister from monitor
            self.vram_monitor.unregister_model(model_name)
            
            # Remove from loaded models
            del self.loaded_models[model_name]
            
            logger.info(f"Unloaded model {model_name}")
    
    def _estimate_vram_usage(self, model_name: str, model_type: str) -> float:
        """Estimate VRAM usage for a model.
        
        Args:
            model_name: Model identifier
            model_type: Model type
            
        Returns:
            Estimated VRAM usage in GB
        """
        # Rough estimates based on model size
        # These are approximations and may vary
        if "phi-3.5-mini" in model_name.lower():
            return 2.0
        elif "qwen2.5-7b" in model_name.lower() or "qwen-7b" in model_name.lower():
            return 14.0
        elif "deberta-v3-small" in model_name.lower():
            return 0.3
        elif "gliner" in model_name.lower() and "small" in model_name.lower():
            return 0.2
        elif "bge-small" in model_name.lower():
            return 0.13
        elif "flan-t5-base" in model_name.lower():
            return 0.25
        elif "faster-whisper-medium" in model_name.lower():
            return 1.5
        elif "vit-gpt2" in model_name.lower():
            return 0.5
        elif "blip-2" in model_name.lower():
            return 5.0
        elif "yolov8n" in model_name.lower():
            return 0.006
        else:
            # Default estimate based on model name patterns
            if "7b" in model_name.lower() or "7B" in model_name:
                return 14.0
            elif "3b" in model_name.lower() or "3B" in model_name:
                return 6.0
            elif "1b" in model_name.lower() or "1B" in model_name:
                return 2.0
            else:
                return 1.0  # Conservative default
    
    def _get_actual_vram_usage(self) -> float:
        """Get actual current VRAM usage.
        
        Returns:
            VRAM usage in GB
        """
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 ** 3)
        return 0.0
    
    def is_loaded(self, model_name: str) -> bool:
        """Check if a model is loaded.
        
        Args:
            model_name: Model identifier
            
        Returns:
            True if model is loaded
        """
        return model_name in self.loaded_models
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """Get a loaded model.
        
        Args:
            model_name: Model identifier
            
        Returns:
            Model instance or None
        """
        if model_name in self.loaded_models:
            return self.loaded_models[model_name].get("model")
        return None
    
    def get_tokenizer(self, model_name: str) -> Optional[Any]:
        """Get a loaded tokenizer.
        
        Args:
            model_name: Model identifier
            
        Returns:
            Tokenizer instance or None
        """
        if model_name in self.loaded_models:
            return self.loaded_models[model_name].get("tokenizer")
        return None
