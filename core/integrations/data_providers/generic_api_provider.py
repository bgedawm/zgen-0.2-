"""
Generic API Provider
----------------
Provides integration with generic RESTful APIs.
"""

import os
import logging
import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse

from ..base import DataProvider

# Setup logger
logger = logging.getLogger(__name__)


class GenericAPIProvider(DataProvider):
    """Generic API data provider for RESTful services."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Base URL is required
        base_url = self.config.get('base_url') or os.getenv('API_BASE_URL')
        if not base_url:
            raise ValueError("API base URL is required. Set 'base_url' in config or API_BASE_URL environment variable.")
        
        # Validate base URL
        parsed_url = urlparse(base_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid API base URL: {base_url}")
        
        # Set default values
        self.config.setdefault('base_url', base_url)
        self.config.setdefault('api_key', self.config.get('api_key') or os.getenv('API_KEY'))
        self.config.setdefault('api_key_header', self.config.get('api_key_header') or os.getenv('API_KEY_HEADER', 'X-API-Key'))
        self.config.setdefault('timeout', int(os.getenv('API_TIMEOUT', '30')))
        self.config.setdefault('headers', {})
        
        # Add API key to headers if provided
        if self.config.get('api_key'):
            self.config['headers'][self.config['api_key_header']] = self.config['api_key']
        
        # Add additional headers from environment variables
        api_headers = os.getenv('API_HEADERS', '')
        if api_headers:
            try:
                headers = json.loads(api_headers)
                self.config['headers'].update(headers)
            except Exception as e:
                logger.warning(f"Failed to parse API_HEADERS: {str(e)}")
    
    def initialize(self) -> None:
        """Initialize the API client."""
        try:
            # Initialize session when needed
            self.session = None
            
            logger.info(f"Initialized generic API provider for {self.config['base_url']}")
        except Exception as e:
            logger.error(f"Error initializing generic API provider: {str(e)}")
            raise
    
    async def _get_session(self):
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config['timeout']),
                headers=self.config['headers']
            )
        return self.session
    
    async def query(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Query data from the API.
        
        Args:
            query: The endpoint or query string
            **kwargs: Additional query parameters
            
        Returns:
            Query results
        """
        try:
            # Determine the HTTP method
            method = kwargs.pop('method', 'GET').upper()
            
            # Build URL
            url = urljoin(self.config['base_url'], query)
            
            # Get session
            session = await self._get_session()
            
            # Prepare request
            request_kwargs = {}
            
            if method in ('GET', 'DELETE'):
                request_kwargs['params'] = kwargs
            else:
                # Determine payload format based on content type
                content_type = self.config['headers'].get('Content-Type', '').lower()
                
                if 'application/x-www-form-urlencoded' in content_type:
                    request_kwargs['data'] = kwargs
                else:
                    # Default to JSON
                    request_kwargs['json'] = kwargs
            
            # Make request
            async with session.request(method, url, **request_kwargs) as response:
                # Check response status
                if response.status < 200 or response.status >= 300:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "status": response.status,
                        "error": error_text
                    }
                
                # Parse response
                try:
                    data = await response.json()
                    return {
                        "success": True,
                        "status": response.status,
                        "data": data
                    }
                except:
                    # Not JSON, return text
                    text = await response.text()
                    return {
                        "success": True,
                        "status": response.status,
                        "data": text
                    }
        
        except Exception as e:
            logger.error(f"Error querying API: {str(e)}")
            
            return {
                "success": False,
                "error": str(e)
            }
    
    async def fetch(self, resource: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch a specific resource from the API.
        
        Args:
            resource: Resource identifier or path
            **kwargs: Additional parameters
            
        Returns:
            Resource data
        """
        # This is similar to query but specifically for GETting a resource
        kwargs['method'] = 'GET'
        return await self.query(resource, **kwargs)
    
    async def create(self, resource: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a resource via the API.
        
        Args:
            resource: Resource endpoint
            data: Resource data
            
        Returns:
            Creation result
        """
        return await self.query(resource, method='POST', **data)
    
    async def update(self, resource: str, resource_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a resource via the API.
        
        Args:
            resource: Resource endpoint
            resource_id: Resource identifier
            data: Updated data
            
        Returns:
            Update result
        """
        endpoint = f"{resource}/{resource_id}"
        return await self.query(endpoint, method='PUT', **data)
    
    async def delete(self, resource: str, resource_id: str) -> Dict[str, Any]:
        """
        Delete a resource via the API.
        
        Args:
            resource: Resource endpoint
            resource_id: Resource identifier
            
        Returns:
            Deletion result
        """
        endpoint = f"{resource}/{resource_id}"
        return await self.query(endpoint, method='DELETE')
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the API integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Try to access the API
            loop = asyncio.get_event_loop()
            
            async def check():
                # Use a health endpoint if provided, otherwise use base URL
                health_endpoint = self.config.get('health_endpoint', '')
                url = urljoin(self.config['base_url'], health_endpoint)
                
                session = await self._get_session()
                async with session.get(url) as response:
                    return {
                        "status": response.status,
                        "data": await response.text() if response.status < 300 else None
                    }
            
            result = loop.run_until_complete(check())
            
            if 200 <= result["status"] < 300:
                return {
                    "status": "healthy",
                    "provider": "generic_api",
                    "base_url": self.config['base_url'],
                    "details": {
                        "http_status": result["status"]
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "generic_api",
                    "base_url": self.config['base_url'],
                    "error": f"API returned status {result['status']}"
                }
        
        except Exception as e:
            logger.error(f"API health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "generic_api",
                "base_url": self.config['base_url'],
                "error": str(e)
            }