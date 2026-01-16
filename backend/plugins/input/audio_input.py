"""Audio input processing plugin (STT)."""

import logging
import asyncio
from typing import Any, Dict, List, Optional
import numpy as np

from .base_input import BaseInputPlugin
from ...core.model_manager import ModelManager
from ...core.vram_monitor import ModelPriority

logger = logging.getLogger(__name__)


class AudioInputPlugin(BaseInputPlugin):
    """Speech-to-text plugin using Faster-Whisper."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "audio_input"
    
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
        self.whisper_model = None
        self.device = "cuda"
        self._lock = asyncio.Lock()
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        from ...core.model_manager import ModelManager
        from ...core.vram_monitor import VRAMMonitor
        
        # Get model manager (injected or create new)
        if hasattr(self, 'model_manager_plugin'):
            self.model_manager = self.model_manager_plugin
        else:
            vram_monitor = VRAMMonitor()
            self.model_manager = ModelManager(vram_monitor)
        
        # Load Faster-Whisper model
        try:
            # Use int8 quantization for lower VRAM usage
            model_name = "guillaumekln/faster-whisper-medium"
            
            # Check VRAM and decide device
            status, used, total = self.model_manager.vram_monitor.get_status()
            if status.value == "critical" or used / total > 0.85:
                self.device = "cpu"
                logger.info("Using CPU for STT due to VRAM pressure")
            
            # Load model asynchronously
            loop = asyncio.get_event_loop()
            self.whisper_model = await loop.run_in_executor(
                None,
                self._load_whisper_model,
                model_name,
                self.device
            )
            
            logger.info(f"Audio input plugin initialized on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def _load_whisper_model(self, model_name: str, device: str):
        """Load Faster-Whisper model synchronously."""
        try:
            from faster_whisper import WhisperModel
            
            model = WhisperModel(
                model_name,
                device=device,
                compute_type="int8" if device == "cuda" else "int8",
                download_root=str(self.model_manager.cache_dir)
            )
            return model
        except ImportError:
            logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
            raise
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        async with self._lock:
            if self.whisper_model is not None:
                del self.whisper_model
                self.whisper_model = None
            
            # Unregister from VRAM monitor
            if self.model_manager:
                self.model_manager.vram_monitor.unregister_model(self.plugin_name)
            
            logger.info("Audio input plugin cleaned up")
    
    async def process(self, content: Any, **kwargs) -> str:
        """Transcribe audio to text.
        
        Args:
            content: Audio data (bytes or file path)
            **kwargs: Additional options (format, sample_rate, etc.)
            
        Returns:
            Transcribed text
        """
        if self.whisper_model is None:
            raise RuntimeError("Whisper model not loaded")
        
        # Handle different input types
        if isinstance(content, str):
            # File path
            audio_path = content
        elif isinstance(content, bytes):
            # Audio bytes - save to temp file
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(content)
                audio_path = f.name
        else:
            raise ValueError(f"Unsupported audio input type: {type(content)}")
        
        try:
            # Transcribe
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                self._transcribe,
                audio_path
            )
            
            # Combine segments
            text = " ".join(segment.text for segment in segments)
            
            logger.info(f"Transcribed audio: {len(text)} characters")
            return text.strip()
            
        finally:
            # Cleanup temp file if created
            if isinstance(content, bytes) and os.path.exists(audio_path):
                os.unlink(audio_path)
    
    def _transcribe(self, audio_path: str):
        """Transcribe audio synchronously."""
        segments, info = self.whisper_model.transcribe(
            audio_path,
            beam_size=5,
            language="en"  # Can be made configurable
        )
        return list(segments), info
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        return 1.5  # Faster-Whisper Medium int8 uses ~1.5GB
