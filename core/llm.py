"""
LLM Integration Module
--------------------
This module provides integration with language models.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from langchain.llms.base import LLM
from langchain.embeddings.base import Embeddings
from langchain.llms import LlamaCpp
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.embeddings import HuggingFaceEmbeddings

from utils.logger import get_logger


class LLMManager:
    """Manages LLM instances and provides access to them."""
    
    def __init__(self):
        """Initialize the LLM manager."""
        self.logger = get_logger(__name__)
        self.llm_instance = None
        self.embedding_model = None
    
    def get_llm(self) -> LLM:
        """
        Get the LLM instance.
        
        Returns:
            An LLM instance
        """
        if self.llm_instance is None:
            self._initialize_llm()
        return self.llm_instance
    
    def get_embeddings(self) -> Embeddings:
        """
        Get the embedding model.
        
        Returns:
            An Embeddings instance
        """
        if self.embedding_model is None:
            self._initialize_embeddings()
        return self.embedding_model
    
    def _initialize_llm(self):
        """Initialize the LLM based on configuration."""
        model_name = os.getenv("LLM_MODEL", "llama2")
        model_path = os.getenv("LLM_MODEL_PATH", "./models/llama-2-7b-chat.gguf")
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        
        self.logger.info(f"Initializing LLM: {model_name} from {model_path}")
        
        # Check if the model file exists
        if not Path(model_path).exists():
            self.logger.warning(f"Model file not found: {model_path}")
            self.logger.warning("Please run the download_model.py script first")
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Create callback manager for streaming output
        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
        
        # Initialize the LLM
        self.llm_instance = LlamaCpp(
            model_path=model_path,
            temperature=temperature,
            max_tokens=max_tokens,
            n_ctx=4096,
            callback_manager=callback_manager,
            verbose=False,
            n_gpu_layers=-1,  # Auto-detect GPU layers
            n_batch=512,
        )
        
        self.logger.info("LLM initialized successfully")
    
    def _initialize_embeddings(self):
        """Initialize the embedding model."""
        model_name = os.getenv("LLM_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        
        self.logger.info(f"Initializing embedding model: {model_name}")
        
        # Initialize embeddings
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cuda"} if os.getenv("USE_GPU", "True").lower() == "true" else {"device": "cpu"}
        )
        
        self.logger.info("Embedding model initialized successfully")


# Singleton instance of LLMManager
_llm_manager = LLMManager()


def get_llm() -> LLM:
    """Get the LLM instance."""
    return _llm_manager.get_llm()


def get_embeddings() -> Embeddings:
    """Get the embedding model."""
    return _llm_manager.get_embeddings()