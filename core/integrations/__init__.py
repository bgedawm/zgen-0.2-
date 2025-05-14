"""
Integrations Package
------------------
This package provides integrations with external tools and APIs.
"""

from core.integrations.llm_providers import (
    OpenAIProvider,
    AnthropicProvider,
    HuggingFaceProvider,
    LocalLLMProvider
)

from core.integrations.notification_providers import (
    SlackProvider,
    EmailProvider,
    DiscordProvider,
    WebhookProvider,
    PushoverProvider
)

from core.integrations.data_providers import (
    WeatherProvider,
    GenericAPIProvider
)

from core.integrations.storage_providers import (
    LocalStorageProvider,
    S3StorageProvider,
    DatabaseStorageProvider
)

# Export all providers
__all__ = [
    # LLM Providers
    'OpenAIProvider',
    'AnthropicProvider',
    'HuggingFaceProvider',
    'LocalLLMProvider',
    
    # Notification Providers
    'SlackProvider',
    'EmailProvider',
    'DiscordProvider',
    'WebhookProvider',
    'PushoverProvider',
    
    # Data Providers
    'WeatherProvider',
    'GenericAPIProvider',
    
    # Storage Providers
    'LocalStorageProvider',
    'S3StorageProvider',
    'DatabaseStorageProvider'
]