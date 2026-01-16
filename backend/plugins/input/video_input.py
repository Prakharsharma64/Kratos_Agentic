"""Video input processing plugin."""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from .base_input import BaseInputPlugin

logger = logging.getLogger(__name__)


class VideoInputPlugin(BaseInputPlugin):
    """Video processing plugin that extracts frames and delegates to image processing."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "video_input"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def dependencies(self) -> List[str]:
        """Dependencies."""
        return ["image_input"]
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        logger.info("Video input plugin initialized")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        logger.info("Video input plugin cleaned up")
    
    async def process(self, content: Any, **kwargs) -> str:
        """Process video by extracting keyframes and analyzing them.
        
        Args:
            content: Video data (bytes, file path, or video object)
            **kwargs: Additional options (frame_interval, etc.)
            
        Returns:
            Video description text
        """
        # Extract keyframes
        frames = await self._extract_frames(content, kwargs.get("frame_interval", 30))
        
        # Get image input plugin
        image_plugin = getattr(self, "image_input_plugin", None)
        if image_plugin is None:
            raise RuntimeError("Image input plugin not available")
        
        # Process each frame
        descriptions = []
        for i, frame in enumerate(frames):
            frame_desc = await image_plugin.process(frame, use_heavy_model=False)
            descriptions.append(f"Frame {i * kwargs.get('frame_interval', 30)}s: {frame_desc}")
        
        # Combine descriptions
        return "\n".join(descriptions)
    
    async def _extract_frames(self, content: Any, interval: int = 30) -> List[Any]:
        """Extract keyframes from video.
        
        Args:
            content: Video content
            interval: Frame interval in seconds
            
        Returns:
            List of frame images
        """
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not installed. Install with: pip install opencv-python")
            raise
        
        # Handle different input types
        if isinstance(content, bytes):
            # Save to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
                f.write(content)
                video_path = f.name
        elif isinstance(content, (str, Path)):
            video_path = str(content)
        else:
            raise ValueError(f"Unsupported video input type: {type(content)}")
        
        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval_frames = int(fps * interval)
            
            frames = []
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % frame_interval_frames == 0:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    from PIL import Image
                    frame_image = Image.fromarray(frame_rgb)
                    frames.append(frame_image)
                
                frame_count += 1
            
            cap.release()
            return frames
            
        finally:
            # Cleanup temp file if created
            if isinstance(content, bytes) and Path(video_path).exists():
                Path(video_path).unlink()
