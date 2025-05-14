"""
LLM Provider Integrations
----------------------
This package contains integrations with language model providers.
"""

import os
import logging
from typing import Dict, Any, Optional

# Import providers
from .openai_provider import OpenAIProvider
from .huggingface_provider import HuggingFaceProvider
from .local_llm_provider import LocalLLMProvider
from .anthropic_provider import AnthropicProvider

# Setup logger
logger = logging.getLogger(__name__)

# Provider registry
_LLM_PROVIDERS = {
    'openai': OpenAIProvider,
    'huggingface': HuggingFaceProvider,
    'local': LocalLLMProvider,
    'anthropic': AnthropicProvider,
}


def get_llm_provider(provider_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
    """
    Get a language model provider instance.
    
    Args:
        provider_name: Name of the provider to use
        config: Optional configuration dictionary
        
    Returns:
        LLM provider instance
        
    Raises:
        ValueError: If the provider is not found
    """
    # Use environment variable if provider name is not specified
    if provider_name is None:
        provider_name = os.getenv('LLM_PROVIDER', 'local').lower()
    
    # Create default config if not provided
    if config is None:
        config = {}
    
    # Validate provider
    if provider_name not in _LLM_PROVIDERS:
        logger.error(f"LLM provider '{provider_name}' not found. Available providers: {list(_LLM_PROVIDERS.keys())}")
        raise ValueError(f"LLM provider '{provider_name}' not found")
    
    # Instantiate provider
    try:
        provider_class = _LLM_PROVIDERS[provider_name]
        provider = provider_class(config)
        logger.info(f"Initialized LLM provider: {provider_name}")
        return provider
    except Exception as e:
        logger.error(f"Failed to initialize LLM provider '{provider_name}': {str(e)}")
        raise