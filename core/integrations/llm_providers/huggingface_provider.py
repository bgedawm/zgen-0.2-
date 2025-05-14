"""
HuggingFace Provider
----------------
Provides integration with HuggingFace's Inference API and local models.
"""

import os
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional

from ..base import LLMProvider

# Setup logger
logger = logging.getLogger(__name__)


class HuggingFaceProvider(LLMProvider):
    """HuggingFace language model provider."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for API key for Inference API (not required for local models)
        api_key = self.config.get('api_key') or os.getenv('HUGGINGFACE_API_KEY')
        
        # Set mode: 'api' or 'local'
        self.config.setdefault('mode', os.getenv('HUGGINGFACE_MODE', 'api'))
        
        if self.config['mode'] == 'api' and not api_key:
            logger.warning("HuggingFace API key not provided. Some models may not be accessible.")
        
        # Set default values
        self.config.setdefault('model', os.getenv('HUGGINGFACE_MODEL', 'google/flan-t5-xl'))
        self.config.setdefault('embedding_model', os.getenv('HUGGINGFACE_EMBEDDING_MODEL', 'sentence-transformers/all-mpnet-base-v2'))
        self.config.setdefault('timeout', int(os.getenv('HUGGINGFACE_TIMEOUT', '120')))
        self.config.setdefault('api_url', os.getenv('HUGGINGFACE_API_URL', 'https://api-inference.huggingface.co/models'))
        
        # Local model settings (only used if mode is 'local')
        if self.config['mode'] == 'local':
            self.config.setdefault('device', os.getenv('HUGGINGFACE_DEVICE', 'cpu'))
            self.config.setdefault('quantization', os.getenv('HUGGINGFACE_QUANTIZATION', None))
            self.config.setdefault('revision', os.getenv('HUGGINGFACE_REVISION', 'main'))
    
    def initialize(self) -> None:
        """Initialize the HuggingFace client."""
        try:
            # Configuration
            self.api_key = self.config.get('api_key') or os.getenv('HUGGINGFACE_API_KEY')
            self.api_url = self.config['api_url']
            self.model = self.config['model']
            self.embedding_model = self.config['embedding_model']
            
            if self.config['mode'] == 'api':
                # Initialize a session for HTTP requests
                self.session = None  # Will be created when needed
                logger.info(f"Initialized HuggingFace API client for model: {self.model}")
            
            else:  # 'local' mode
                # Import here to avoid dependencies if not using local mode
                try:
                    from transformers import AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoTokenizer
                    from sentence_transformers import SentenceTransformer
                    self.transformers_available = True
                except ImportError:
                    logger.error("transformers and sentence_transformers packages are required for local mode")
                    self.transformers_available = False
                    raise ValueError("transformers and sentence_transformers packages are required for local mode")
                
                logger.info(f"Loading local HuggingFace model: {self.model}")
                
                # Load tokenizer for text generation
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model, 
                    revision=self.config['revision']
                )
                
                # Determine model type and load accordingly
                model_info = self._get_model_info()
                
                if model_info['model_type'] in ['t5', 'bart', 'mt5']:
                    # Sequence-to-sequence models
                    self.hf_model = AutoModelForSeq2SeqLM.from_pretrained(
                        self.model,
                        revision=self.config['revision'],
                        device_map=self.config['device'],
                        load_in_8bit=self.config['quantization'] == '8bit',
                        load_in_4bit=self.config['quantization'] == '4bit'
                    )
                else:
                    # Causal language models
                    self.hf_model = AutoModelForCausalLM.from_pretrained(
                        self.model,
                        revision=self.config['revision'],
                        device_map=self.config['device'],
                        load_in_8bit=self.config['quantization'] == '8bit',
                        load_in_4bit=self.config['quantization'] == '4bit'
                    )
                
                # Load embedding model if different from main model
                if self.embedding_model != self.model:
                    logger.info(f"Loading embedding model: {self.embedding_model}")
                    self.embedding_model_instance = SentenceTransformer(self.embedding_model)
                else:
                    self.embedding_model_instance = None
                
                logger.info(f"Initialized local HuggingFace model: {self.model}")
        
        except Exception as e:
            logger.error(f"Error initializing HuggingFace client: {str(e)}")
            raise
    
    def _get_model_info(self):
        """Get model type information from HuggingFace API."""
        try:
            import requests
            
            # Query the Hugging Face API for model information
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            url = f"https://huggingface.co/api/models/{self.model}"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                model_info = response.json()
                return {
                    'model_type': model_info.get('pipeline_tag') or 'text-generation',
                    'architecture': model_info.get('config', {}).get('architectures', ['Unknown'])[0]
                }
            else:
                logger.warning(f"Failed to get model info from HuggingFace: {response.status_code}")
                # Make a reasonable guess based on model name
                if 't5' in self.model.lower():
                    return {'model_type': 't5', 'architecture': 'T5ForConditionalGeneration'}
                elif 'bart' in self.model.lower():
                    return {'model_type': 'bart', 'architecture': 'BartForConditionalGeneration'}
                else:
                    return {'model_type': 'text-generation', 'architecture': 'AutoModelForCausalLM'}
        
        except Exception as e:
            logger.warning(f"Error getting model info: {str(e)}. Using default.")
            return {'model_type': 'text-generation', 'architecture': 'AutoModelForCausalLM'}
    
    async def _get_session(self):
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config['timeout']),
                headers=headers
            )
        return self.session
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text using HuggingFace models.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters for the API
            
        Returns:
            Generated text
        """
        try:
            if self.config['mode'] == 'api':
                return await self._generate_text_api(prompt, **kwargs)
            else:
                return await self._generate_text_local(prompt, **kwargs)
        
        except Exception as e:
            logger.error(f"Error generating text with HuggingFace: {str(e)}")
            raise
    
    async def _generate_text_api(self, prompt: str, **kwargs) -> str:
        """Generate text using HuggingFace Inference API."""
        try:
            # Prepare parameters
            params = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": kwargs.get('max_tokens', 256),
                    "temperature": kwargs.get('temperature', 0.7),
                    "top_p": kwargs.get('top_p', 0.9),
                    "do_sample": kwargs.get('do_sample', True),
                }
            }
            
            # Get session
            session = await self._get_session()
            
            # Make request
            async with session.post(f"{self.api_url}/{self.model}", json=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"HuggingFace API returned status {response.status}: {error_text}")
                
                response_data = await response.json()
                
                # Extract response based on response format
                if isinstance(response_data, list) and len(response_data) > 0:
                    if 'generated_text' in response_data[0]:
                        return response_data[0]['generated_text']
                    else:
                        return str(response_data[0])
                elif isinstance(response_data, dict):
                    if 'generated_text' in response_data:
                        return response_data['generated_text']
                    else:
                        return str(response_data)
                else:
                    return str(response_data)
        
        except Exception as e:
            logger.error(f"Error with HuggingFace Inference API: {str(e)}")
            raise
    
    async def _generate_text_local(self, prompt: str, **kwargs) -> str:
        """Generate text using local HuggingFace model."""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Prepare parameters
            params = {
                "max_new_tokens": kwargs.get('max_tokens', 256),
                "temperature": kwargs.get('temperature', 0.7),
                "top_p": kwargs.get('top_p', 0.9),
                "do_sample": kwargs.get('do_sample', True),
            }
            
            # Get model type
            model_type = self._get_model_info()['model_type']
            
            # Define the generation function
            def generate():
                inputs = self.tokenizer(prompt, return_tensors="pt").to(self.config['device'])
                
                if model_type in ['t5', 'bart', 'mt5']:
                    # For seq2seq models
                    outputs = self.hf_model.generate(
                        inputs.input_ids,
                        **params
                    )
                    return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                else:
                    # For causal LMs
                    outputs = self.hf_model.generate(
                        inputs.input_ids,
                        **params
                    )
                    # Return only the newly generated text, not the prompt
                    generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                    
                    # Remove prompt from output if it's included
                    if generated_text.startswith(prompt):
                        return generated_text[len(prompt):].strip()
                    return generated_text
            
            # Run in executor
            return await loop.run_in_executor(None, generate)
        
        except Exception as e:
            logger.error(f"Error with local HuggingFace model: {str(e)}")
            raise
    
    async def generate_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a response based on a conversation.
        
        Args:
            messages: List of messages in the conversation
            **kwargs: Additional parameters for the API
            
        Returns:
            Generated response
        """
        try:
            # Convert chat messages to prompt format
            prompt = self._format_chat_messages(messages)
            
            # Use regular text generation
            return await self.generate_text(prompt, **kwargs)
        
        except Exception as e:
            logger.error(f"Error generating chat response with HuggingFace: {str(e)}")
            raise
    
    def _format_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format chat messages into a prompt for non-chat models."""
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
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for a text.
        
        Args:
            text: The input text
            
        Returns:
            Embedding vector
        """
        try:
            if self.config['mode'] == 'api':
                return await self._embed_text_api(text)
            else:
                return await self._embed_text_local(text)
        
        except Exception as e:
            logger.error(f"Error generating embeddings with HuggingFace: {str(e)}")
            raise
    
    async def _embed_text_api(self, text: str) -> List[float]:
        """Generate embeddings using HuggingFace Inference API."""
        try:
            # Prepare parameters
            params = {
                "inputs": text
            }
            
            # Get session
            session = await self._get_session()
            
            # Make request
            async with session.post(f"{self.api_url}/{self.embedding_model}", json=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"HuggingFace API returned status {response.status}: {error_text}")
                
                response_data = await response.json()
                
                # Extract embeddings
                if isinstance(response_data, list) and len(response_data) > 0:
                    return response_data[0]
                else:
                    return response_data
        
        except Exception as e:
            logger.error(f"Error with HuggingFace Embeddings API: {str(e)}")
            raise
    
    async def _embed_text_local(self, text: str) -> List[float]:
        """Generate embeddings using local model."""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Define the embedding function
            def embed():
                if self.embedding_model_instance:
                    # Use dedicated embedding model
                    return self.embedding_model_instance.encode(text).tolist()
                else:
                    # Use tokenizer and model embeddings 
                    inputs = self.tokenizer(text, return_tensors="pt").to(self.config['device'])
                    with torch.no_grad():
                        outputs = self.hf_model(**inputs, output_hidden_states=True)
                        # Use last hidden state of the first token as embedding
                        embeddings = outputs.hidden_states[-1][:, 0, :].cpu().numpy()
                        return embeddings[0].tolist()
            
            # Run in executor
            return await loop.run_in_executor(None, embed)
        
        except Exception as e:
            logger.error(f"Error with local HuggingFace embeddings: {str(e)}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the HuggingFace integration.
        
        Returns:
            Dictionary with health status
        """
        if self.config['mode'] == 'api':
            try:
                # Create a simple request to check if the API is accessible
                loop = asyncio.get_event_loop()
                
                async def check():
                    session = await self._get_session()
                    # Test with a simple query
                    params = {"inputs": "Hello"}
                    async with session.post(f"{self.api_url}/{self.model}", json=params) as response:
                        if response.status != 200:
                            raise Exception(f"HuggingFace API returned status {response.status}")
                        
                        return await response.json()
                
                response = loop.run_until_complete(check())
                
                return {
                    "status": "healthy",
                    "provider": "huggingface",
                    "mode": "api",
                    "model": self.model,
                    "details": {
                        "response_sample": str(response)[:100] + "..." if len(str(response)) > 100 else str(response)
                    }
                }
            
            except Exception as e:
                logger.error(f"HuggingFace API health check failed: {str(e)}")
                
                return {
                    "status": "unhealthy",
                    "provider": "huggingface",
                    "mode": "api",
                    "model": self.model,
                    "error": str(e)
                }
        else:
            # Local model health check
            try:
                if not hasattr(self, 'hf_model') or self.hf_model is None:
                    raise Exception("Local model not initialized")
                
                # Just check if we can tokenize something simple
                tokens = self.tokenizer("Hello, world!").input_ids
                
                return {
                    "status": "healthy",
                    "provider": "huggingface",
                    "mode": "local",
                    "model": self.model,
                    "details": {
                        "device": self.config['device'],
                        "tokenizer_vocab_size": len(self.tokenizer)
                    }
                }
            
            except Exception as e:
                logger.error(f"HuggingFace local model health check failed: {str(e)}")
                
                return {
                    "status": "unhealthy",
                    "provider": "huggingface",
                    "mode": "local",
                    "model": self.model,
                    "error": str(e)
                }