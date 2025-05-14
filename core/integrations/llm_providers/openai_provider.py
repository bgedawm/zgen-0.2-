"""
OpenAI LLM Provider
----------------
Provides integration with OpenAI's language models.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional

import openai
from openai import AsyncOpenAI

from ..base import LLMProvider

# Setup logger
logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI language model provider."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for API key
        api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key is required. Set 'api_key' in config or OPENAI_API_KEY environment variable.")
        
        # Set default values
        self.config.setdefault('model', os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'))
        self.config.setdefault('temperature', float(os.getenv('OPENAI_TEMPERATURE', '0.7')))
        self.config.setdefault('top_p', float(os.getenv('OPENAI_TOP_P', '1.0')))
        self.config.setdefault('timeout', int(os.getenv('OPENAI_TIMEOUT', '120')))
        self.config.setdefault('streaming', os.getenv('OPENAI_STREAMING', 'false').lower() == 'true')
        self.config.setdefault('embedding_model', os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002'))
        
        # Custom base URL (for Azure or self-hosted deployments)
        base_url = self.config.get('base_url') or os.getenv('OPENAI_BASE_URL')
        if base_url:
            self.config['base_url'] = base_url
    
    def initialize(self) -> None:
        """Initialize the OpenAI client."""
        try:
            # Configuration
            api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
            base_url = self.config.get('base_url')
            
            # Initialize client
            client_kwargs = {
                'api_key': api_key,
                'timeout': self.config['timeout']
            }
            
            if base_url:
                client_kwargs['base_url'] = base_url
            
            self.client = AsyncOpenAI(**client_kwargs)
            
            logger.info(f"Initialized OpenAI client with model: {self.config['model']}")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            raise
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text using OpenAI's completions API.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters for the API
            
        Returns:
            Generated text
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
                return await self._generate_text_streaming(prompt, params)
            
            # Create messages for chat models (default)
            messages = [{"role": "user", "content": prompt}]
            
            # Use chat API for chat models
            if 'gpt' in params['model'] or 'turbo' in params['model']:
                response = await self.client.chat.completions.create(
                    messages=messages,
                    **params
                )
                return response.choices[0].message.content
            else:
                # Use completions API for non-chat models
                response = await self.client.completions.create(
                    prompt=prompt,
                    **params
                )
                return response.choices[0].text
        
        except Exception as e:
            logger.error(f"Error generating text with OpenAI: {str(e)}")
            raise
    
    async def _generate_text_streaming(self, prompt: str, params: Dict[str, Any]) -> str:
        """
        Generate text using OpenAI's streaming API.
        
        Args:
            prompt: The input prompt
            params: API parameters
            
        Returns:
            Generated text
        """
        try:
            # Create messages for chat models
            messages = [{"role": "user", "content": prompt}]
            
            # Use chat API for chat models
            if 'gpt' in params['model'] or 'turbo' in params['model']:
                response_stream = await self.client.chat.completions.create(
                    messages=messages,
                    **params
                )
                
                full_text = ""
                async for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_text += chunk.choices[0].delta.content
                
                return full_text
            else:
                # Use completions API for non-chat models
                response_stream = await self.client.completions.create(
                    prompt=prompt,
                    **params
                )
                
                full_text = ""
                async for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].text:
                        full_text += chunk.choices[0].text
                
                return full_text
        
        except Exception as e:
            logger.error(f"Error generating streaming text with OpenAI: {str(e)}")
            raise
    
    async def generate_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a response based on a conversation using OpenAI's chat API.
        
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
            
            # Use chat API
            response = await self.client.chat.completions.create(
                messages=messages,
                **params
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Error generating chat response with OpenAI: {str(e)}")
            raise
    
    async def _generate_chat_response_streaming(self, messages: List[Dict[str, str]], params: Dict[str, Any]) -> str:
        """
        Generate a chat response using OpenAI's streaming API.
        
        Args:
            messages: List of messages in the conversation
            params: API parameters
            
        Returns:
            Generated response
        """
        try:
            response_stream = await self.client.chat.completions.create(
                messages=messages,
                **params
            )
            
            full_text = ""
            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_text += chunk.choices[0].delta.content
            
            return full_text
        
        except Exception as e:
            logger.error(f"Error generating streaming chat response with OpenAI: {str(e)}")
            raise
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for a text using OpenAI's embeddings API.
        
        Args:
            text: The input text
            
        Returns:
            Embedding vector
        """
        try:
            response = await self.client.embeddings.create(
                model=self.config['embedding_model'],
                input=text
            )
            
            return response.data[0].embedding
        
        except Exception as e:
            logger.error(f"Error generating embeddings with OpenAI: {str(e)}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the OpenAI integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to check if the API is accessible
            loop = asyncio.get_event_loop()
            models = loop.run_until_complete(self.client.models.list())
            
            available_models = [model.id for model in models.data]
            
            # Check if the configured model is available
            model_available = self.config['model'] in available_models
            
            return {
                "status": "healthy" if model_available else "degraded",
                "provider": "openai",
                "model": self.config['model'],
                "model_available": model_available,
                "details": {
                    "available_models": available_models[:10]  # Limit to avoid huge response
                }
            }
        
        except Exception as e:
            logger.error(f"OpenAI health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "openai",
                "model": self.config['model'],
                "error": str(e)
            }