"""
Base Integration Classes
---------------------
This module contains base classes for integrations with external services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union


class Integration(ABC):
    """Base class for all integrations."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the integration.
        
        Args:
            config: Configuration dictionary for the integration
        """
        self.config = config
        self.name = self.__class__.__name__
        self._validate_config()
        self.initialize()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the integration.
        
        This is called after the configuration is validated.
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the integration.
        
        Returns:
            Dictionary with health status
        """
        pass


class LLMProvider(Integration):
    """Base class for language model providers."""
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text based on a prompt.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters for the LLM
            
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    async def generate_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a response based on a conversation.
        
        Args:
            messages: List of messages in the conversation
            **kwargs: Additional parameters for the LLM
            
        Returns:
            Generated response
        """
        pass
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for a text.
        
        Args:
            text: The input text
            
        Returns:
            Embedding vector
        """
        pass


class NotificationProvider(Integration):
    """Base class for notification providers."""
    
    @abstractmethod
    async def send_notification(self, 
                               message: str, 
                               title: Optional[str] = None, 
                               level: str = "info", 
                               recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send a notification.
        
        Args:
            message: Notification message
            title: Optional notification title
            level: Notification level (info, warning, error, success)
            recipients: Optional list of recipients
            
        Returns:
            Dictionary with send status
        """
        pass


class DataProvider(Integration):
    """Base class for data providers."""
    
    @abstractmethod
    async def query(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Query data from the provider.
        
        Args:
            query: Query string
            **kwargs: Additional query parameters
            
        Returns:
            Query results
        """
        pass
    
    @abstractmethod
    async def fetch(self, resource: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch a specific resource from the provider.
        
        Args:
            resource: Resource identifier
            **kwargs: Additional fetch parameters
            
        Returns:
            Resource data
        """
        pass


class StorageProvider(Integration):
    """Base class for storage providers."""
    
    @abstractmethod
    async def store(self, key: str, data: Any) -> Dict[str, Any]:
        """
        Store data.
        
        Args:
            key: Storage key
            data: Data to store
            
        Returns:
            Storage status
        """
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> Any:
        """
        Retrieve data.
        
        Args:
            key: Storage key
            
        Returns:
            Retrieved data
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> Dict[str, Any]:
        """
        Delete data.
        
        Args:
            key: Storage key
            
        Returns:
            Deletion status
        """
        pass
    
    @abstractmethod
    async def list(self, prefix: Optional[str] = None) -> List[str]:
        """
        List storage keys.
        
        Args:
            prefix: Optional key prefix filter
            
        Returns:
            List of keys
        """
        pass