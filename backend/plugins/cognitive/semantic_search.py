"""Semantic search plugin using Qdrant."""

import logging
from typing import Any, Dict, List, Optional

from .base_cognitive import BaseCognitivePlugin

logger = logging.getLogger(__name__)


class SemanticSearchPlugin(BaseCognitivePlugin):
    """Semantic search using Qdrant vector database."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "semantic_search"
    
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
        self.collection_name = "documents"
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
            
            logger.info(f"Semantic search plugin initialized (Qdrant: {qdrant_url})")
        except ImportError:
            logger.warning("Qdrant client not installed. Install with: pip install qdrant-client")
            self.qdrant_client = None
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            self.qdrant_client = None
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        logger.info("Semantic search plugin cleaned up")
    
    async def process(self, query: str, top_k: int = 5, **kwargs) -> Dict[str, Any]:
        """Perform semantic search.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            **kwargs: Additional options
            
        Returns:
            Search results with ranked documents
        """
        if self.qdrant_client is None:
            return {"results": [], "count": 0}
        
        # Get embedding plugin
        if self.embedding_plugin is None:
            self.embedding_plugin = getattr(self, "embedding_agent_plugin", None)
        
        if self.embedding_plugin is None:
            logger.warning("Embedding plugin not available for semantic search")
            return {"results": [], "count": 0}
        
        # Generate query embedding
        query_embedding = await self.embedding_plugin.process(query, normalize=True)
        
        # Convert to list if numpy array
        if hasattr(query_embedding, "tolist"):
            query_vector = query_embedding.tolist()
        else:
            query_vector = query_embedding
        
        # Search
        try:
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            
            # Format results
            results = [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload or {}
                }
                for result in search_results
            ]
            
            return {
                "results": results,
                "count": len(results),
                "query": query
            }
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return {"results": [], "count": 0}
    
    async def add_documents(self, documents: List[Dict[str, Any]], embeddings: Optional[List] = None) -> None:
        """Add documents to the search index.
        
        Args:
            documents: List of documents with id, text, and optional metadata
            embeddings: Optional pre-computed embeddings
        """
        if self.qdrant_client is None:
            logger.warning("Qdrant client not available")
            return
        
        # Get embedding plugin
        if self.embedding_plugin is None:
            self.embedding_plugin = getattr(self, "embedding_agent_plugin", None)
        
        if self.embedding_plugin is None:
            logger.warning("Embedding plugin not available")
            return
        
        # Generate embeddings if not provided
        if embeddings is None:
            texts = [doc.get("text", "") for doc in documents]
            embeddings = await self.embedding_plugin.process(texts, normalize=True)
        
        # Prepare points
        points = []
        for i, doc in enumerate(documents):
            embedding = embeddings[i]
            if hasattr(embedding, "tolist"):
                vector = embedding.tolist()
            else:
                vector = embedding
            
            points.append({
                "id": doc.get("id", i),
                "vector": vector,
                "payload": {
                    "text": doc.get("text", ""),
                    **doc.get("metadata", {})
                }
            })
        
        # Upsert to Qdrant
        try:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Added {len(documents)} documents to search index")
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
