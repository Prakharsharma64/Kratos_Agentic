"""Audio input/output endpoints."""

from fastapi import APIRouter, UploadFile, File, Depends
from typing import AsyncIterator

from ..schemas import AudioRequest, AudioResponse, StreamingChunk
from ...core.orchestrator import Orchestrator, RequestType
from ...core.plugin_manager import PluginManager
from ...core.plugin_registry import PluginRegistry

router = APIRouter(prefix="/audio", tags=["audio"])


def get_orchestrator() -> Orchestrator:
    """Dependency to get orchestrator."""
    from ...core.plugin_manager import PluginManager
    from ...core.plugin_registry import PluginRegistry
    registry = PluginRegistry()
    plugin_manager = PluginManager(registry)
    return Orchestrator(plugin_manager)


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...)
) -> dict:
    """Transcribe audio to text."""
    # Read audio file
    audio_data = await file.read()
    
    # TODO: Use audio input plugin to transcribe
    return {
        "text": "Transcription coming soon",
        "metadata": {
            "format": file.content_type,
            "size": len(audio_data)
        }
    }


@router.post("/synthesize")
async def synthesize_speech(
    text: str,
    format: str = "wav"
) -> AudioResponse:
    """Synthesize text to speech."""
    # TODO: Use audio output plugin to synthesize
    return AudioResponse(
        audio_data=b"",
        format=format,
        sample_rate=16000
    )


@router.post("/stream")
async def audio_stream(
    file: UploadFile = File(...)
) -> AsyncIterator[StreamingChunk]:
    """Stream audio processing and response."""
    orchestrator = get_orchestrator()
    
    # Read audio file
    audio_data = await file.read()
    
    # Process request
    async for chunk in orchestrator.process_request(
        RequestType.AUDIO,
        audio_data,
        {"format": file.content_type}
    ):
        yield StreamingChunk(
            type=chunk.get("type", "text"),
            content=chunk.get("content", ""),
            metadata=chunk.get("metadata", {})
        )
    
    # Send done signal
    yield StreamingChunk(
        type="done",
        content="",
        metadata={}
    )
