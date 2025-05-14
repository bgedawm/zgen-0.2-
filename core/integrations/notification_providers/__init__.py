"""
Notification Provider Integrations
------------------------------
This package contains integrations with notification services.
"""

import os
import logging
from typing import Dict, Any, Optional

# Import providers
from .email_provider import EmailProvider
from .slack_provider import SlackProvider
from .discord_provider import DiscordProvider
from .pushover_provider import PushoverProvider
from .webhook_provider import WebhookProvider

# Setup logger
logger = logging.getLogger(__name__)

# Provider registry
_NOTIFICATION_PROVIDERS = {
    'email': EmailProvider,
    'slack': SlackProvider,
    'discord': DiscordProvider,
    'pushover': PushoverProvider,
    'webhook': WebhookProvider,
}


def get_notification_provider(provider_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
    """
    Get a notification provider instance.
    
    Args:
        provider_name: Name of the provider to use
        config: Optional configuration dictionary
        
    Returns:
        Notification provider instance
        
    Raises:
        ValueError: If the provider is not found
    """
    # Use environment variable if provider name is not specified
    if provider_name is None:
        provider_name = os.getenv('NOTIFICATION_PROVIDER', 'webhook').lower()
    
    # Create default config if not provided
    if config is None:
        config = {}
    
    # Validate provider
    if provider_name not in _NOTIFICATION_PROVIDERS:
        logger.error(f"Notification provider '{provider_name}' not found. Available providers: {list(_NOTIFICATION_PROVIDERS.keys())}")
        raise ValueError(f"Notification provider '{provider_name}' not found")
    
    # Instantiate provider
    try:
        provider_class = _NOTIFICATION_PROVIDERS[provider_name]
        provider = provider_class(config)
        logger.info(f"Initialized notification provider: {provider_name}")
        return provider
    except Exception as e:
        logger.error(f"Failed to initialize notification provider '{provider_name}': {str(e)}")
        raise