"""
Data Provider Integrations
----------------------
This package contains integrations with external data sources.
"""

import os
import logging
from typing import Dict, Any, Optional

# Import providers
from .weather_provider import WeatherProvider
from .news_provider import NewsProvider
from .finance_provider import FinanceProvider
from .database_provider import DatabaseProvider
from .generic_api_provider import GenericAPIProvider

# Setup logger
logger = logging.getLogger(__name__)

# Provider registry
_DATA_PROVIDERS = {
    'weather': WeatherProvider,
    'news': NewsProvider,
    'finance': FinanceProvider,
    'database': DatabaseProvider,
    'generic_api': GenericAPIProvider,
}


def get_data_provider(provider_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
    """
    Get a data provider instance.
    
    Args:
        provider_name: Name of the provider to use
        config: Optional configuration dictionary
        
    Returns:
        Data provider instance
        
    Raises:
        ValueError: If the provider is not found
    """
    # Use environment variable if provider name is not specified
    if provider_name is None:
        provider_name = os.getenv('DATA_PROVIDER', 'generic_api').lower()
    
    # Create default config if not provided
    if config is None:
        config = {}
    
    # Validate provider
    if provider_name not in _DATA_PROVIDERS:
        logger.error(f"Data provider '{provider_name}' not found. Available providers: {list(_DATA_PROVIDERS.keys())}")
        raise ValueError(f"Data provider '{provider_name}' not found")
    
    # Instantiate provider
    try:
        provider_class = _DATA_PROVIDERS[provider_name]
        provider = provider_class(config)
        logger.info(f"Initialized data provider: {provider_name}")
        return provider
    except Exception as e:
        logger.error(f"Failed to initialize data provider '{provider_name}': {str(e)}")
        raise