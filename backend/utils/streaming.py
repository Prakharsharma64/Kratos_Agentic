"""Streaming utilities."""

from typing import AsyncIterator, Dict, Any
import json


async def format_streaming_chunk(chunk_type: str, content: Any, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Format a streaming chunk.
    
    Args:
        chunk_type: Chunk type (text, audio, council_update, error, done)
        content: Chunk content
        metadata: Optional metadata
        
    Returns:
        Formatted chunk dictionary
    """
    return {
        "type": chunk_type,
        "content": content,
        "metadata": metadata or {}
    }


async def stream_text(text: str, chunk_size: int = 10) -> AsyncIterator[str]:
    """Stream text in chunks.
    
    Args:
        text: Text to stream
        chunk_size: Words per chunk
        
    Yields:
        Text chunks
    """
    words = text.split()
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        if i + chunk_size < len(words):
            chunk += " "
        yield chunk
