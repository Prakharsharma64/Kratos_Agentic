"""Image input processing plugin."""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from io import BytesIO
from PIL import Image

from .base_input import BaseInputPlugin
from ...core.model_manager import ModelManager
from ...core.vram_monitor import ModelPriority, VRAMStatus

logger = logging.getLogger(__name__)


class ImageInputPlugin(BaseInputPlugin):
    """Image understanding plugin with two-tier processing."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "image_input"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def dependencies(self) -> List[str]:
        """Dependencies."""
        return []
    
    def __init__(self):
        """Initialize plugin."""
        self.model_manager: Optional[ModelManager] = None
        self.light_model = None  # ViT-GPT2
        self.heavy_model = None  # BLIP-2
        self.device = "cuda"
        self._lock = asyncio.Lock()
    
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
        
        # Load light model (always)
        try:
            model_name = "nlpconnect/vit-gpt2-image-captioning"
            loop = asyncio.get_event_loop()
            self.light_model, self.tokenizer = await loop.run_in_executor(
                None,
                self._load_light_model,
                model_name
            )
            logger.info("Image input plugin initialized (light model)")
        except Exception as e:
            logger.error(f"Failed to load image model: {e}")
            raise
    
    def _load_light_model(self, model_name: str):
        """Load light image model synchronously."""
        from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
        
        model = VisionEncoderDecoderModel.from_pretrained(model_name)
        processor = ViTImageProcessor.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        if self.device == "cuda":
            model = model.to(self.device)
        
        return model, (processor, tokenizer)
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        async with self._lock:
            if self.light_model is not None:
                del self.light_model
                self.light_model = None
            
            if self.heavy_model is not None:
                del self.heavy_model
                self.heavy_model = None
            
            if self.model_manager:
                self.model_manager.vram_monitor.unregister_model(self.plugin_name)
            
            logger.info("Image input plugin cleaned up")
    
    async def process(self, content: Any, **kwargs) -> str:
        """Process image and return description.
        
        Args:
            content: Image data (bytes, PIL Image, or file path)
            **kwargs: Additional options (use_heavy_model, etc.)
            
        Returns:
            Image description text
        """
        # Load image
        if isinstance(content, bytes):
            image = Image.open(BytesIO(content))
        elif isinstance(content, str):
            image = Image.open(content)
        elif isinstance(content, Image.Image):
            image = content
        else:
            raise ValueError(f"Unsupported image input type: {type(content)}")
        
        # Check if we should use heavy model
        use_heavy = kwargs.get("use_heavy_model", False)
        
        # Check VRAM before using heavy model
        if use_heavy:
            status, used, total = self.model_manager.vram_monitor.get_status()
            if status == VRAMStatus.CRITICAL or (used / total) > 0.85:
                logger.warning("VRAM pressure detected, using light model instead")
                use_heavy = False
        
        if use_heavy and self.heavy_model is None:
            # Load heavy model on demand
            await self._load_heavy_model()
        
        # Process image
        if use_heavy and self.heavy_model is not None:
            return await self._process_heavy(image)
        else:
            return await self._process_light(image)
    
    async def _process_light(self, image: Image.Image) -> str:
        """Process image with light model."""
        if self.light_model is None:
            raise RuntimeError("Light model not loaded")
        
        processor, tokenizer = self.tokenizer
        
        loop = asyncio.get_event_loop()
        description = await loop.run_in_executor(
            None,
            self._caption_image_light,
            image,
            processor,
            tokenizer
        )
        
        return description
    
    def _caption_image_light(self, image: Image.Image, processor, tokenizer) -> str:
        """Caption image with light model synchronously."""
        # Preprocess
        pixel_values = processor(images=image, return_tensors="pt").pixel_values
        if self.device == "cuda":
            pixel_values = pixel_values.to(self.device)
        
        # Generate
        generated_ids = self.light_model.generate(pixel_values, max_length=50)
        generated_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return generated_text
    
    async def _load_heavy_model(self) -> None:
        """Load heavy model (BLIP-2) on demand."""
        async with self._lock:
            if self.heavy_model is not None:
                return
            
            # Check VRAM
            can_load, reason = self.model_manager.vram_monitor.can_load_model(5.0, ModelPriority.MEDIUM)
            if not can_load:
                logger.warning(f"Cannot load heavy model: {reason}")
                return
            
            try:
                # Load BLIP-2
                # Note: BLIP-2 loading is complex, this is a placeholder
                logger.info("Loading BLIP-2 model...")
                # TODO: Implement BLIP-2 loading
                logger.warning("BLIP-2 loading not yet implemented, using light model")
            except Exception as e:
                logger.error(f"Failed to load heavy model: {e}")
    
    async def _process_heavy(self, image: Image.Image) -> str:
        """Process image with heavy model."""
        # TODO: Implement BLIP-2 processing
        return await self._process_light(image)
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        usage = 0.5  # Light model
        if self.heavy_model is not None:
            usage += 5.0  # Heavy model
        return usage
