"""Chat endpoints."""

from fastapi import APIRouter, Depends
from typing import AsyncIterator

from ..schemas import ChatRequest, ChatResponse, StreamingChunk
from ...core.orchestrator import Orchestrator, RequestType
from ...core.plugin_manager import PluginManager
from ...core.plugin_registry import PluginRegistry

router = APIRouter(prefix="/chat", tags=["chat"])


def get_orchestrator() -> Orchestrator:
    """Dependency to get orchestrator."""
    from ...core.plugin_manager import PluginManager
    from ...core.plugin_registry import PluginRegistry
    registry = PluginRegistry()
    plugin_manager = PluginManager(registry)
    return Orchestrator(plugin_manager)


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint (non-streaming)."""
    # TODO: Implement non-streaming chat
    return ChatResponse(
        response="Chat functionality coming soon",
        metadata={}
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> AsyncIterator[StreamingChunk]:
    """Streaming chat endpoint."""
    orchestrator = get_orchestrator()
    
    # Map request type
    request_type_map = {
        "text": RequestType.TEXT,
        "audio": RequestType.AUDIO,
        "image": RequestType.IMAGE,
        "video": RequestType.VIDEO
    }
    req_type = request_type_map.get(request.request_type.value, RequestType.TEXT)
    
    # Process request
    async for chunk in orchestrator.process_request(
        req_type,
        request.message,
        request.metadata
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
