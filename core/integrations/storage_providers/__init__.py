"""
Storage Provider Integrations
--------------------------
This package contains integrations with storage services.
"""

import os
import logging
from typing import Dict, Any, Optional

# Import providers
from .local_storage_provider import LocalStorageProvider
from .s3_storage_provider import S3StorageProvider
from .database_storage_provider import DatabaseStorageProvider

# Setup logger
logger = logging.getLogger(__name__)

# Provider registry
_STORAGE_PROVIDERS = {
    'local': LocalStorageProvider,
    's3': S3StorageProvider,
    'database': DatabaseStorageProvider,
}


def get_storage_provider(provider_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
    """
    Get a storage provider instance.
    
    Args:
        provider_name: Name of the provider to use
        config: Optional configuration dictionary
        
    Returns:
        Storage provider instance
        
    Raises:
        ValueError: If the provider is not found
    """
    # Use environment variable if provider name is not specified
    if provider_name is None:
        provider_name = os.getenv('STORAGE_PROVIDER', 'local').lower()
    
    # Create default config if not provided
    if config is None:
        config = {}
    
    # Validate provider
    if provider_name not in _STORAGE_PROVIDERS:
        logger.error(f"Storage provider '{provider_name}' not found. Available providers: {list(_STORAGE_PROVIDERS.keys())}")
        raise ValueError(f"Storage provider '{provider_name}' not found")
    
    # Instantiate provider
    try:
        provider_class = _STORAGE_PROVIDERS[provider_name]
        provider = provider_class(config)
        logger.info(f"Initialized storage provider: {provider_name}")
        return provider
    except Exception as e:
        logger.error(f"Failed to initialize storage provider '{provider_name}': {str(e)}")
        raise