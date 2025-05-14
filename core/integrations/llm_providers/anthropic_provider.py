"""
Anthropic LLM Provider
------------------
Provides integration with Anthropic's Claude models.
"""

import os
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional

from ..base import LLMProvider

# Setup logger
logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic language model provider."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for API key
        api_key = self.config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("Anthropic API key is required. Set 'api_key' in config or ANTHROPIC_API_KEY environment variable.")
        
        # Set default values
        self.config.setdefault('model', os.getenv('ANTHROPIC_MODEL', 'claude-3-opus-20240229'))
        self.config.setdefault('temperature', float(os.getenv('ANTHROPIC_TEMPERATURE', '0.7')))
        self.config.setdefault('top_p', float(os.getenv('ANTHROPIC_TOP_P', '1.0')))
        self.config.setdefault('timeout', int(os.getenv('ANTHROPIC_TIMEOUT', '120')))
        self.config.setdefault('streaming', os.getenv('ANTHROPIC_STREAMING', 'false').lower() == 'true')
        
        # API endpoints
        self.config.setdefault('api_url', os.getenv('ANTHROPIC_API_URL', 'https://api.anthropic.com/v1'))
        self.version = "2023-06-01"  # Anthropic API version
    
    def initialize(self) -> None:
        """Initialize the Anthropic client."""
        try:
            # Configuration
            self.api_key = self.config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
            self.api_url = self.config['api_url']
            
            # Initialize a session for HTTP requests
            self.session = None  # Will be created when needed
            
            logger.info(f"Initialized Anthropic client with model: {self.config['model']}")
        except Exception as e:
            logger.error(f"Error initializing Anthropic client: {str(e)}")
            raise
    
    async def _get_session(self):
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config['timeout']),
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.version,
                    "content-type": "application/json"
                }
            )
        return self.session
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text using Anthropic's API.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters for the API
            
        Returns:
            Generated text
        """
        try:
            # Convert to chat format
            messages = [{"role": "user", "content": prompt}]
            
            # Use chat API
            return await self.generate_chat_response(messages, **kwargs)
        
        except Exception as e:
            logger.error(f"Error generating text with Anthropic: {str(e)}")
            raise
    
    async def generate_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a response based on a conversation using Anthropic's API.
        
        Args:
            messages: List of messages in the conversation
            **kwargs: Additional parameters for the API
            
        Returns:
            Generated response
        """
        try:
            # Merge config with kwargs
            params = {
                'model': self.config['model'],
                'temperature': self.config['temperature'],
                'top_p': self.config['top_p'],
                'stream': self.config['streaming'],
                'max_tokens': kwargs.get('max_tokens', 1000),
            }
            
            # Override with any kwargs
            params.update(kwargs)
            
            # Handle streaming
            if params['stream']:
                return await self._generate_chat_response_streaming(messages, params)
            
            # Prepare request
            payload = {
                "model": params['model'],
                "messages": messages,
                "temperature": params['temperature'],
                "top_p": params['top_p'],
                "max_tokens": params['max_tokens'],
            }
            
            # Get session
            session = await self._get_session()
            
            # Make request
            async with session.post(f"{self.api_url}/messages", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API returned status {response.status}: {error_text}")
                
                response_data = await response.json()
                
                return response_data['content'][0]['text']
        
        except Exception as e:
            logger.error(f"Error generating chat response with Anthropic: {str(e)}")
            raise
    
    async def _generate_chat_response_streaming(self, messages: List[Dict[str, str]], params: Dict[str, Any]) -> str:
        """
        Generate a chat response using Anthropic's streaming API.
        
        Args:
            messages: List of messages in the conversation
            params: API parameters
            
        Returns:
            Generated response
        """
        try:
            # Prepare request
            payload = {
                "model": params['model'],
                "messages": messages,
                "temperature": params['temperature'],
                "top_p": params['top_p'],
                "max_tokens": params['max_tokens'],
                "stream": True,
            }
            
            # Get session
            session = await self._get_session()
            
            # Make request
            full_text = ""
            
            async with session.post(f"{self.api_url}/messages", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API returned status {response.status}: {error_text}")
                
                # Process streaming response
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line and line.startswith('data:'):
                        # Remove 'data:' prefix
                        data_str = line[5:].strip()
                        
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            if 'delta' in data and 'text' in data['delta']:
                                full_text += data['delta']['text']
                        except:
                            pass
            
            return full_text
        
        except Exception as e:
            logger.error(f"Error generating streaming chat response with Anthropic: {str(e)}")
            raise
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for a text.
        
        Args:
            text: The input text
            
        Returns:
            Embedding vector
        """
        # Note: Anthropic does not currently provide a public embeddings API.
        # This is implemented to maintain compatibility with the LLMProvider interface.
        logger.warning("Anthropic does not provide embeddings API. Returning empty embedding.")
        return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Anthropic integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to check if the API is accessible
            loop = asyncio.get_event_loop()
            
            async def check():
                session = await self._get_session()
                # Just check if we can access the API
                async with session.get(f"{self.api_url}/models") as response:
                    if response.status != 200:
                        raise Exception(f"Anthropic API returned status {response.status}")
                    
                    data = await response.json()
                    return data
            
            models_data = loop.run_until_complete(check())
            
            # Extract available models
            available_models = [model['id'] for model in models_data.get('models', [])]
            
            # Check if the configured model is available
            model_available = self.config['model'] in available_models
            
            return {
                "status": "healthy" if model_available else "degraded",
                "provider": "anthropic",
                "model": self.config['model'],
                "model_available": model_available,
                "details": {
                    "available_models": available_models  # Anthropic has fewer models than OpenAI
                }
            }
        
        except Exception as e:
            logger.error(f"Anthropic health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "anthropic",
                "model": self.config['model'],
                "error": str(e)
            }