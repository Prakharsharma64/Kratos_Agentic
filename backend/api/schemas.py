"""Pydantic schemas for request/response models."""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class RequestType(str, Enum):
    """Request type enumeration."""
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    request_type: RequestType = Field(default=RequestType.TEXT, description="Request type")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Assistant response")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Response metadata")


class AudioRequest(BaseModel):
    """Audio input request model."""
    audio_data: bytes = Field(..., description="Audio data (base64 encoded or raw bytes)")
    format: str = Field(default="wav", description="Audio format (wav, mp3, etc.)")
    sample_rate: Optional[int] = Field(default=None, description="Audio sample rate")


class AudioResponse(BaseModel):
    """Audio output response model."""
    audio_data: bytes = Field(..., description="Generated audio data")
    format: str = Field(default="wav", description="Audio format")
    sample_rate: int = Field(default=16000, description="Audio sample rate")


class ImageRequest(BaseModel):
    """Image input request model."""
    image_data: bytes = Field(..., description="Image data (base64 encoded or raw bytes)")
    format: str = Field(default="jpeg", description="Image format (jpeg, png, webp)")
    description: Optional[str] = Field(default=None, description="Optional image description")


class ImageResponse(BaseModel):
    """Image analysis response model."""
    description: str = Field(..., description="Image description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Image metadata")


class PluginInfo(BaseModel):
    """Plugin information model."""
    name: str
    type: str
    version: str
    status: str
    healthy: bool
    vram_usage_gb: float
    dependencies: List[str]


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(default="healthy", description="System status")
    plugins: Dict[str, PluginInfo] = Field(default_factory=dict, description="Plugin health status")
    vram: Optional[Dict[str, Any]] = Field(default=None, description="VRAM status")


class StreamingChunk(BaseModel):
    """Streaming response chunk model."""
    type: str = Field(..., description="Chunk type (text, audio, council_update, error, done)")
    content: Union[str, bytes, Dict[str, Any]] = Field(..., description="Chunk content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Chunk metadata")
