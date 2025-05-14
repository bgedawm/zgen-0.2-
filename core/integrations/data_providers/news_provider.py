"""
News Data Provider
---------------
Provides integration with news APIs for retrieving news articles.
"""

import os
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from ..base import DataProvider

# Setup logger
logger = logging.getLogger(__name__)


class NewsProvider(DataProvider):
    """News data provider for retrieving news articles."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for API key
        api_key = self.config.get('api_key') or os.getenv('NEWS_API_KEY')
        if not api_key:
            raise ValueError("News API key is required. Set 'api_key' in config or NEWS_API_KEY environment variable.")
        
        # Set default values
        self.config.setdefault('api_key', api_key)
        self.config.setdefault('base_url', self.config.get('base_url') or os.getenv('NEWS_API_URL', 'https://newsapi.org/v2'))
        self.config.setdefault('timeout', int(os.getenv('NEWS_API_TIMEOUT', '30')))
        self.config.setdefault('language', self.config.get('language') or os.getenv('NEWS_API_LANGUAGE', 'en'))
        self.config.setdefault('country', self.config.get('country') or os.getenv('NEWS_API_COUNTRY', 'us'))
        self.config.setdefault('page_size', int(os.getenv('NEWS_API_PAGE_SIZE', '10')))
    
    def initialize(self) -> None:
        """Initialize the News API client."""
        try:
            # Initialize session when needed
            self.session = None
            
            logger.info(f"Initialized News API provider with base URL: {self.config['base_url']}")
        except Exception as e:
            logger.error(f"Error initializing News API provider: {str(e)}")
            raise
    
    async def _get_session(self):
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config['timeout'])
            )
        return self.session
    
    async def query(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Query news articles based on keywords.
        
        Args:
            query: Search query
            **kwargs: Additional query parameters
            
        Returns:
            Query results
        """
        try:
            # Get session
            session = await self._get_session()
            
            # Build query parameters
            params = {
                'q': query,
                'language': kwargs.get('language', self.config['language']),
                'pageSize': kwargs.get('page_size', self.config['page_size']),
                'page': kwargs.get('page', 1),
                'apiKey': self.config['api_key']
            }
            
            # Add optional parameters
            if 'from_date' in kwargs:
                params['from'] = kwargs['from_date']
            elif 'days' in kwargs:
                days = int(kwargs['days'])
                from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                params['from'] = from_date
            
            if 'to_date' in kwargs:
                params['to'] = kwargs['to_date']
            
            if 'sort_by' in kwargs:
                params['sortBy'] = kwargs['sort_by']
            
            # Make API request
            url = f"{self.config['base_url']}/everything"
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"News API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                if data.get('status') != 'ok':
                    raise Exception(f"News API error: {data.get('message', 'Unknown error')}")
                
                # Process and format results
                articles = data.get('articles', [])
                
                return {
                    'success': True,
                    'query': query,
                    'total_results': data.get('totalResults', 0),
                    'articles': articles,
                    'metadata': {
                        'page': params['page'],
                        'page_size': params['pageSize'],
                        'language': params['language']
                    }
                }
        
        except Exception as e:
            logger.error(f"Error querying News API: {str(e)}")
            
            return {
                'success': False,
                'query': query,
                'error': str(e)
            }
    
    async def fetch(self, resource: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch news based on a specific resource.
        
        Args:
            resource: Resource type (top, sources, category)
            **kwargs: Additional fetch parameters
            
        Returns:
            Resource data
        """
        try:
            # Get session
            session = await self._get_session()
            
            if resource.lower() == 'top':
                # Get top headlines
                params = {
                    'language': kwargs.get('language', self.config['language']),
                    'country': kwargs.get('country', self.config['country']),
                    'pageSize': kwargs.get('page_size', self.config['page_size']),
                    'page': kwargs.get('page', 1),
                    'apiKey': self.config['api_key']
                }
                
                # Add category if specified
                if 'category' in kwargs:
                    params['category'] = kwargs['category']
                
                # Make API request
                url = f"{self.config['base_url']}/top-headlines"
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"News API returned status {response.status}: {error_text}")
                    
                    data = await response.json()
                    
                    if data.get('status') != 'ok':
                        raise Exception(f"News API error: {data.get('message', 'Unknown error')}")
                    
                    # Process and format results
                    articles = data.get('articles', [])
                    
                    return {
                        'success': True,
                        'resource': 'top_headlines',
                        'total_results': data.get('totalResults', 0),
                        'articles': articles,
                        'metadata': {
                            'page': params['page'],
                            'page_size': params['pageSize'],
                            'country': params['country'],
                            'category': params.get('category', 'all')
                        }
                    }
            
            elif resource.lower() == 'sources':
                # Get news sources
                params = {
                    'language': kwargs.get('language', self.config['language']),
                    'country': kwargs.get('country', self.config['country']),
                    'apiKey': self.config['api_key']
                }
                
                # Add category if specified
                if 'category' in kwargs:
                    params['category'] = kwargs['category']
                
                # Make API request
                url = f"{self.config['base_url']}/sources"
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"News API returned status {response.status}: {error_text}")
                    
                    data = await response.json()
                    
                    if data.get('status') != 'ok':
                        raise Exception(f"News API error: {data.get('message', 'Unknown error')}")
                    
                    # Process and format results
                    sources = data.get('sources', [])
                    
                    return {
                        'success': True,
                        'resource': 'sources',
                        'sources': sources,
                        'metadata': {
                            'total': len(sources),
                            'country': params['country'],
                            'language': params['language'],
                            'category': params.get('category', 'all')
                        }
                    }
            
            else:
                raise ValueError(f"Unsupported resource type: {resource}. Supported types are 'top' and 'sources'.")
        
        except Exception as e:
            logger.error(f"Error fetching from News API: {str(e)}")
            
            return {
                'success': False,
                'resource': resource,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the News API integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to check if the API is accessible
            loop = asyncio.get_event_loop()
            
            async def check():
                session = await self._get_session()
                
                # Try to fetch sources (lightweight request)
                params = {
                    'apiKey': self.config['api_key'],
                    'language': self.config['language'],
                    'country': self.config['country']
                }
                
                url = f"{self.config['base_url']}/sources"
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return False, f"API returned status {response.status}"
                    
                    data = await response.json()
                    return data.get('status') == 'ok', data.get('message', 'Unknown error')
            
            is_healthy, message = loop.run_until_complete(check())
            
            if is_healthy:
                return {
                    "status": "healthy",
                    "provider": "news",
                    "message": "API is accessible",
                    "details": {
                        "base_url": self.config['base_url'],
                        "language": self.config['language'],
                        "country": self.config['country']
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "news",
                    "error": message
                }
        
        except Exception as e:
            logger.error(f"News API health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "news",
                "error": str(e)
            }