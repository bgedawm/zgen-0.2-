"""
Local LLM Provider
--------------
Provides integration with locally running LLM models via llama-cpp-python.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional

from ..base import LLMProvider

# Setup logger
logger = logging.getLogger(__name__)


class LocalLLMProvider(LLMProvider):
    """Local language model provider using llama-cpp-python."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Model path is required
        model_path = self.config.get('model_path') or os.getenv('LOCAL_LLM_MODEL_PATH')
        if not model_path:
            raise ValueError("Local LLM model path is required. Set 'model_path' in config or LOCAL_LLM_MODEL_PATH environment variable.")
        
        # Set default values
        self.config.setdefault('model_path', model_path)
        self.config.setdefault('n_ctx', int(os.getenv('LOCAL_LLM_N_CTX', '2048')))
        self.config.setdefault('n_batch', int(os.getenv('LOCAL_LLM_N_BATCH', '512')))
        self.config.setdefault('n_threads', int(os.getenv('LOCAL_LLM_N_THREADS', '4')))
        self.config.setdefault('n_gpu_layers', int(os.getenv('LOCAL_LLM_N_GPU_LAYERS', '0')))
        self.config.setdefault('temperature', float(os.getenv('LOCAL_LLM_TEMPERATURE', '0.7')))
        self.config.setdefault('top_p', float(os.getenv('LOCAL_LLM_TOP_P', '0.9')))
        self.config.setdefault('repeat_penalty', float(os.getenv('LOCAL_LLM_REPEAT_PENALTY', '1.1')))
        self.config.setdefault('embedding_mode', os.getenv('LOCAL_LLM_EMBEDDING_MODE', 'false').lower() == 'true')
        
        # Model format specific settings
        self.config.setdefault('format', os.getenv('LOCAL_LLM_FORMAT', 'gguf'))
        
        # Chat format related settings
        self.config.setdefault('chat_format', os.getenv('LOCAL_LLM_CHAT_FORMAT', 'llama2'))
    
    def initialize(self) -> None:
        """Initialize the local LLM."""
        try:
            # Import llama_cpp
            try:
                from llama_cpp import Llama
                self.llama_cpp_available = True
            except ImportError:
                logger.error("llama-cpp-python package is required for LocalLLMProvider")
                self.llama_cpp_available = False
                raise ValueError("llama-cpp-python package is required for LocalLLMProvider")
            
            model_path = self.config['model_path']
            
            # Check if model file exists
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                raise ValueError(f"Model file not found: {model_path}")
            
            logger.info(f"Loading local LLM model: {model_path}")
            
            # Initialize the LLM
            self.llm = Llama(
                model_path=model_path,
                n_ctx=self.config['n_ctx'],
                n_batch=self.config['n_batch'],
                n_threads=self.config['n_threads'],
                n_gpu_layers=self.config['n_gpu_layers'],
                embedding=self.config['embedding_mode']
            )
            
            logger.info(f"Local LLM model loaded successfully: {model_path}")
        
        except Exception as e:
            logger.error(f"Error initializing local LLM: {str(e)}")
            raise
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text using the local LLM.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters for the LLM
            
        Returns:
            Generated text
        """
        try:
            # Merge config with kwargs
            params = {
                'temperature': self.config['temperature'],
                'top_p': self.config['top_p'],
                'repeat_penalty': self.config['repeat_penalty'],
                'max_tokens': kwargs.get('max_tokens', 512),
            }
            
            # Override with any kwargs
            params.update(kwargs)
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Define the generation function
            def generate():
                output = self.llm(
                    prompt,
                    max_tokens=params['max_tokens'],
                    temperature=params['temperature'],
                    top_p=params['top_p'],
                    repeat_penalty=params['repeat_penalty'],
                    echo=False
                )
                
                return output['choices'][0]['text']
            
            # Run in executor
            return await loop.run_in_executor(None, generate)
        
        except Exception as e:
            logger.error(f"Error generating text with local LLM: {str(e)}")
            raise
    
    async def generate_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a response based on a conversation.
        
        Args:
            messages: List of messages in the conversation
            **kwargs: Additional parameters for the LLM
            
        Returns:
            Generated response
        """
        try:
            # Format messages according to the chat format
            prompt = self._format_chat_messages(messages)
            
            # Use regular text generation
            return await self.generate_text(prompt, **kwargs)
        
        except Exception as e:
            logger.error(f"Error generating chat response with local LLM: {str(e)}")
            raise
    
    def _format_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format chat messages according to the model's chat format."""
        chat_format = self.config['chat_format'].lower()
        
        if chat_format == 'llama2':
            return self._format_llama2(messages)
        elif chat_format == 'alpaca':
            return self._format_alpaca(messages)
        elif chat_format == 'vicuna':
            return self._format_vicuna(messages)
        elif chat_format == 'chatml':
            return self._format_chatml(messages)
        else:
            # Default to a simple format
            return self._format_simple(messages)
    
    def _format_simple(self, messages: List[Dict[str, str]]) -> str:
        """Format messages in a simple way."""
        prompt = ""
        
        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'system':
                prompt += f"System: {content}\n\n"
            elif role == 'user':
                prompt += f"User: {content}\n\n"
            elif role == 'assistant':
                prompt += f"Assistant: {content}\n\n"
            else:
                prompt += f"{role.capitalize()}: {content}\n\n"
        
        # Add assistant prefix for the response
        prompt += "Assistant: "
        
        return prompt
    
    def _format_llama2(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Llama 2 chat models."""
        system_prompt = "You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe."
        
        # Extract system message if present
        for message in messages:
            if message.get('role') == 'system':
                system_prompt = message.get('content', system_prompt)
                break
        
        # Build the prompt
        prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n"
        
        # Add user/assistant conversation
        for i, message in enumerate(messages):
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'system':
                # Already handled
                continue
            elif role == 'user':
                if i > 0 and messages[i-1].get('role') == 'assistant':
                    # This is a follow-up user message after an assistant response
                    prompt += f"[INST] {content} [/INST]"
                else:
                    # First user message or after another user message
                    prompt += f"{content} [/INST]"
            elif role == 'assistant':
                prompt += f" {content} </s><s>[INST] "
        
        # Ensure prompt ends with user message
        if not prompt.endswith('[/INST]'):
            prompt += "[/INST]"
        
        return prompt
    
    def _format_alpaca(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Alpaca-style models."""
        prompt = ""
        
        # Extract system message if present
        system_content = None
        for message in messages:
            if message.get('role') == 'system':
                system_content = message.get('content')
                break
        
        if system_content:
            prompt += f"### Instruction:\n{system_content}\n\n"
        
        # Add user/assistant conversation
        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'system':
                # Already handled
                continue
            elif role == 'user':
                prompt += f"### Input:\n{content}\n\n"
            elif role == 'assistant':
                prompt += f"### Response:\n{content}\n\n"
        
        # Add final response prompt
        prompt += "### Response:\n"
        
        return prompt
    
    def _format_vicuna(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Vicuna-style models."""
        prompt = ""
        
        # Handle system message
        system_content = None
        for message in messages:
            if message.get('role') == 'system':
                system_content = message.get('content')
                break
        
        if system_content:
            prompt += f"SYSTEM: {system_content}\n\n"
        
        # Add user/assistant conversation
        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'system':
                # Already handled
                continue
            elif role == 'user':
                prompt += f"USER: {content}\n\n"
            elif role == 'assistant':
                prompt += f"ASSISTANT: {content}\n\n"
        
        # Add final response prompt
        prompt += "ASSISTANT: "
        
        return prompt
    
    def _format_chatml(self, messages: List[Dict[str, str]]) -> str:
        """Format messages in ChatML format."""
        prompt = ""
        
        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'system':
                prompt += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == 'user':
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == 'assistant':
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
            else:
                prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
        
        # Add assistant prefix for the response
        prompt += "<|im_start|>assistant\n"
        
        return prompt
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for a text.
        
        Args:
            text: The input text
            
        Returns:
            Embedding vector
        """
        try:
            if not self.config['embedding_mode']:
                logger.warning("Embedding mode is not enabled. Set embedding_mode=True in config.")
                return []
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Define the embedding function
            def embed():
                return self.llm.embed(text)
            
            # Run in executor
            return await loop.run_in_executor(None, embed)
        
        except Exception as e:
            logger.error(f"Error generating embeddings with local LLM: {str(e)}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the local LLM integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Test a simple generation
            loop = asyncio.get_event_loop()
            
            def test_generation():
                return self.llm("Hello", max_tokens=5, echo=False)
            
            _ = loop.run_until_complete(asyncio.to_thread(test_generation))
            
            return {
                "status": "healthy",
                "provider": "local_llm",
                "model": self.config['model_path'],
                "details": {
                    "n_ctx": self.config['n_ctx'],
                    "n_gpu_layers": self.config['n_gpu_layers'],
                    "embedding_mode": self.config['embedding_mode'],
                    "format": self.config['format']
                }
            }
        
        except Exception as e:
            logger.error(f"Local LLM health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "local_llm",
                "model": self.config['model_path'],
                "error": str(e)
            }