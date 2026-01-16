"""Vector memory plugin using Qdrant."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from .base_memory import BaseMemoryPlugin

logger = logging.getLogger(__name__)


class VectorMemoryPlugin(BaseMemoryPlugin):
    """Vector-based memory storage with confidence scoring."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "vector_memory"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def dependencies(self) -> List[str]:
        """Dependencies."""
        return ["embedding_agent"]
    
    def __init__(self):
        """Initialize plugin."""
        self.qdrant_client = None
        self.collection_name = "memories"
        self.embedding_plugin = None
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            
            # Initialize Qdrant client
            qdrant_url = config.get("qdrant_url", "http://localhost:6333")
            self.qdrant_client = QdrantClient(url=qdrant_url)
            
            # Create collection if it doesn't exist
            try:
                self.qdrant_client.get_collection(self.collection_name)
            except:
                # Collection doesn't exist, create it
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # BGE-small embedding size
                        distance=Distance.COSINE
                    )
                )
            
            logger.info(f"Vector memory plugin initialized (Qdrant: {qdrant_url})")
        except ImportError:
            logger.warning("Qdrant client not installed")
            self.qdrant_client = None
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            self.qdrant_client = None
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        logger.info("Vector memory plugin cleaned up")
    
    async def process(self, input_text: str, output_text: str = None, metadata: Dict[str, Any] = None, 
                     **kwargs) -> Dict[str, Any]:
        """Store or retrieve memory.
        
        Args:
            input_text: User input text
            output_text: System response text (for storage)
            metadata: Additional metadata
            **kwargs: Additional options (operation, query, etc.)
            
        Returns:
            Memory operation result
        """
        operation = kwargs.get("operation", "store")
        
        if operation == "store":
            return await self._store_memory(input_text, output_text, metadata)
        elif operation == "retrieve":
            return await self._retrieve_memories(input_text, kwargs.get("top_k", 5))
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    async def _store_memory(self, input_text: str, output_text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Store a memory entry."""
        if self.qdrant_client is None:
            return {"stored": False, "error": "Qdrant not available"}
        
        # Get embedding plugin
        if self.embedding_plugin is None:
            self.embedding_plugin = getattr(self, "embedding_agent_plugin", None)
        
        if self.embedding_plugin is None:
            return {"stored": False, "error": "Embedding plugin not available"}
        
        # Generate embedding for input
        embedding = await self.embedding_plugin.process(input_text, normalize=True)
        
        # Convert to list
        if hasattr(embedding, "tolist"):
            vector = embedding.tolist()
        else:
            vector = embedding
        
        # Create memory entry
        memory_id = str(uuid.uuid4())
        confidence = metadata.get("confidence", 0.7) if metadata else 0.7
        source = metadata.get("source", "inference") if metadata else "inference"
        decay_rate = metadata.get("decay_rate", 0.02) if metadata else 0.02
        
        memory_entry = {
            "id": memory_id,
            "vector": vector,
            "payload": {
                "content": f"Input: {input_text}\nOutput: {output_text}" if output_text else input_text,
                "input": input_text,
                "output": output_text,
                "confidence": confidence,
                "source": source,
                "last_verified": datetime.now().isoformat(),
                "decay_rate": decay_rate,
                "created_at": datetime.now().isoformat(),
                **metadata or {}
            }
        }
        
        # Store in Qdrant
        try:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[memory_entry]
            )
            return {"stored": True, "id": memory_id}
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return {"stored": False, "error": str(e)}
    
    async def _retrieve_memories(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Retrieve relevant memories."""
        if self.qdrant_client is None:
            return {"memories": [], "count": 0}
        
        # Get embedding plugin
        if self.embedding_plugin is None:
            self.embedding_plugin = getattr(self, "embedding_agent_plugin", None)
        
        if self.embedding_plugin is None:
            return {"memories": [], "count": 0}
        
        # Generate query embedding
        query_embedding = await self.embedding_plugin.process(query, normalize=True)
        
        # Convert to list
        if hasattr(query_embedding, "tolist"):
            query_vector = query_embedding.tolist()
        else:
            query_vector = query_embedding
        
        # Search
        try:
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            
            # Format results
            memories = [
                {
                    "id": result.id,
                    "content": result.payload.get("content", ""),
                    "confidence": result.payload.get("confidence", 0.5),
                    "score": result.score,
                    "metadata": {k: v for k, v in result.payload.items() 
                               if k not in ["content", "confidence"]}
                }
                for result in results
            ]
            
            return {"memories": memories, "count": len(memories)}
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return {"memories": [], "count": 0}
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        return 0.0  # Qdrant doesn't use VRAM
