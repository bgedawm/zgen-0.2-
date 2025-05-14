"""
Agent Memory Module
----------------
This module provides memory capabilities for the agent.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

import chromadb
from langchain.vectorstores import Chroma
from langchain.schema import Document

from core.llm import get_embeddings
from utils.logger import get_logger


class AgentMemory:
    """Provides memory capabilities for the agent."""
    
    def __init__(self):
        """Initialize the agent memory."""
        self.logger = get_logger(__name__)
        
        # Get memory configuration
        self.memory_type = os.getenv("MEMORY_TYPE", "chroma")
        self.memory_path = Path(os.getenv("MEMORY_PATH", "./data/memory"))
        
        # Make sure the memory directory exists
        self.memory_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize the vector store
        self._initialize_vector_store()
        
        # Recent memory cache (for faster access to recent items)
        self.recent_memory: List[Dict[str, Any]] = []
        self.max_recent_items = 100
        
        self.logger.info(f"Agent memory initialized ({self.memory_type})")
    
    def _initialize_vector_store(self):
        """Initialize the vector store based on configuration."""
        embeddings = get_embeddings()
        
        if self.memory_type == "chroma":
            self.vector_store = Chroma(
                persist_directory=str(self.memory_path),
                embedding_function=embeddings
            )
        else:
            self.logger.warning(f"Unknown memory type: {self.memory_type}, using Chroma")
            self.vector_store = Chroma(
                persist_directory=str(self.memory_path),
                embedding_function=embeddings
            )
    
    async def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add an item to memory.
        
        Args:
            content: The content to remember
            metadata: Additional metadata for the memory
            
        Returns:
            The memory ID
        """
        if metadata is None:
            metadata = {}
        
        # Add a timestamp if not provided
        if "timestamp" not in metadata:
            metadata["timestamp"] = datetime.now().isoformat()
        
        # Add a memory ID if not provided
        if "memory_id" not in metadata:
            from uuid import uuid4
            metadata["memory_id"] = str(uuid4())
        
        # Add the source if not provided
        if "source" not in metadata:
            metadata["source"] = "user_interaction"
        
        # Create a document for the vector store
        document = Document(
            page_content=content,
            metadata=metadata
        )
        
        # Add to vector store
        self.vector_store.add_documents([document])
        
        # Add to recent memory
        memory_item = {
            "content": content,
            "metadata": metadata
        }
        self.recent_memory.insert(0, memory_item)
        
        # Trim recent memory if needed
        if len(self.recent_memory) > self.max_recent_items:
            self.recent_memory = self.recent_memory[:self.max_recent_items]
        
        self.logger.debug(f"Added memory: {metadata['memory_id']}")
        
        return metadata["memory_id"]
    
    async def search_memory(self, query: str, k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search memory for relevant items.
        
        Args:
            query: The search query
            k: Number of results to return
            filter_metadata: Metadata filters
            
        Returns:
            List of memory items
        """
        self.logger.debug(f"Searching memory: {query}")
        
        # Search the vector store
        docs_and_scores = self.vector_store.similarity_search_with_score(
            query, k=k, filter=filter_metadata
        )
        
        # Format the results
        results = []
        for doc, score in docs_and_scores:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance": score
            })
        
        return results
    
    async def get_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a memory item by ID.
        
        Args:
            memory_id: The memory ID
            
        Returns:
            The memory item or None if not found
        """
        # First check recent memory (faster)
        for item in self.recent_memory:
            if item["metadata"].get("memory_id") == memory_id:
                return item
        
        # Then check the vector store
        filter_metadata = {"memory_id": memory_id}
        results = self.vector_store.get(filter=filter_metadata)
        
        if results and len(results) > 0:
            return {
                "content": results[0].page_content,
                "metadata": results[0].metadata
            }
        
        return None
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory item.
        
        Args:
            memory_id: The memory ID
            
        Returns:
            True if successful, False otherwise
        """
        # Also remove from recent memory
        self.recent_memory = [item for item in self.recent_memory 
                             if item["metadata"].get("memory_id") != memory_id]
        
        # Remove from vector store
        filter_metadata = {"memory_id": memory_id}
        self.vector_store.delete(filter=filter_metadata)
        
        self.logger.debug(f"Deleted memory: {memory_id}")
        
        return True
    
    async def clear_memory(self) -> bool:
        """
        Clear all memory.
        
        Returns:
            True if successful, False otherwise
        """
        # Clear recent memory
        self.recent_memory = []
        
        # Clear vector store
        self.vector_store.delete(filter={})
        
        self.logger.info("Cleared all memory")
        
        return True
    
    async def get_recent_memories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent memories.
        
        Args:
            limit: Maximum number of memories to return
            
        Returns:
            List of recent memory items
        """
        return self.recent_memory[:limit]