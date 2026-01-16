"""Image processing endpoints."""

from fastapi import APIRouter, UploadFile, File
from typing import AsyncIterator

from ..schemas import ImageRequest, ImageResponse, StreamingChunk
from ...core.orchestrator import Orchestrator, RequestType

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...)
) -> ImageResponse:
    """Analyze an image."""
    # Read image file
    image_data = await file.read()
    
    # TODO: Use image input plugin to analyze
    return ImageResponse(
        description="Image analysis coming soon",
        metadata={
            "format": file.content_type,
            "size": len(image_data)
        }
    )


@router.post("/stream")
async def image_stream(
    file: UploadFile = File(...)
) -> AsyncIterator[StreamingChunk]:
    """Stream image processing and response."""
    orchestrator = Orchestrator(None)  # TODO: Get from dependency
    
    # Read image file
    image_data = await file.read()
    
    # Process request
    async for chunk in orchestrator.process_request(
        RequestType.IMAGE,
        image_data,
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
