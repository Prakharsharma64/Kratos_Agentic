"""Audio output plugin (TTS)."""

import logging
import asyncio
import io
from typing import Any, Dict, List, AsyncIterator, Optional

from .base_output import BaseOutputPlugin
from ...core.vram_monitor import VRAMStatus

logger = logging.getLogger(__name__)


class AudioOutputPlugin(BaseOutputPlugin):
    """Text-to-speech plugin using Piper or XTTS."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "audio_output"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    def __init__(self):
        """Initialize plugin."""
        self.piper_model = None
        self.xtts_model = None
        self.use_xtts = False
        self.device = "cpu"  # Default to CPU for TTS
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        from ...core.vram_monitor import VRAMMonitor
        
        # Check VRAM to decide TTS engine
        vram_monitor = VRAMMonitor()
        status, used, total = vram_monitor.get_status()
        
        # Use XTTS if VRAM available, otherwise Piper
        if status.value != "critical" and (used / total) < 0.80:
            self.use_xtts = config.get("use_xtts", False)
            self.device = "cuda" if config.get("device", "cuda") == "cuda" else "cpu"
        else:
            self.use_xtts = False
            self.device = "cpu"
        
        # Load appropriate model
        if self.use_xtts:
            await self._load_xtts()
        else:
            await self._load_piper()
        
        logger.info(f"Audio output plugin initialized ({'XTTS' if self.use_xtts else 'Piper'})")
    
    async def _load_piper(self) -> None:
        """Load Piper TTS model."""
        try:
            # Piper TTS loading (simplified)
            # In production, would use actual Piper library
            logger.info("Piper TTS model loaded (placeholder)")
            self.piper_model = "piper_loaded"
        except Exception as e:
            logger.error(f"Failed to load Piper: {e}")
            self.piper_model = None
    
    async def _load_xtts(self) -> None:
        """Load XTTS-v2 model."""
        try:
            # XTTS-v2 loading (simplified)
            # In production, would use actual XTTS library
            logger.info("XTTS-v2 model loaded (placeholder)")
            self.xtts_model = "xtts_loaded"
        except Exception as e:
            logger.error(f"Failed to load XTTS: {e}")
            # Fallback to Piper
            await self._load_piper()
            self.use_xtts = False
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        self.piper_model = None
        self.xtts_model = None
        logger.info("Audio output plugin cleaned up")
    
    async def process(self, content: str, **kwargs) -> AsyncIterator[bytes]:
        """Generate audio from text (progressive streaming).
        
        Args:
            content: Text content
            **kwargs: Additional options (voice, sample_rate, etc.)
            
        Yields:
            Audio chunks (WAV/MP3 bytes)
        """
        # Progressive streaming: start TTS immediately
        # Split text into sentences for chunked generation
        sentences = self._split_sentences(content)
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            # Generate audio for sentence
            if self.use_xtts and self.xtts_model:
                audio_chunk = await self._synthesize_xtts(sentence, **kwargs)
            elif self.piper_model:
                audio_chunk = await self._synthesize_piper(sentence, **kwargs)
            else:
                # Fallback: generate silence
                audio_chunk = self._generate_silence(1.0)
            
            yield audio_chunk
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    async def _synthesize_piper(self, text: str, **kwargs) -> bytes:
        """Synthesize using Piper TTS."""
        # Placeholder - in production would use actual Piper
        sample_rate = kwargs.get("sample_rate", 22050)
        
        # Generate silence as placeholder
        return self._generate_silence(len(text) * 0.1)  # Rough estimate
    
    async def _synthesize_xtts(self, text: str, **kwargs) -> bytes:
        """Synthesize using XTTS-v2."""
        # Placeholder - in production would use actual XTTS
        sample_rate = kwargs.get("sample_rate", 24000)
        voice = kwargs.get("voice", "default")
        
        # Generate silence as placeholder
        return self._generate_silence(len(text) * 0.1)
    
    def _generate_silence(self, duration_seconds: float, sample_rate: int = 22050) -> bytes:
        """Generate silence audio (placeholder)."""
        import numpy as np
        import wave
        
        num_samples = int(duration_seconds * sample_rate)
        silence = np.zeros(num_samples, dtype=np.int16)
        
        # Convert to WAV bytes
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(silence.tobytes())
        
        return buffer.getvalue()
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        if self.use_xtts and self.xtts_model:
            return 2.0
        return 0.05  # Piper is very lightweight
