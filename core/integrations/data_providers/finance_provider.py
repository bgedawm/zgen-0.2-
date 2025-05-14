"""
Finance Data Provider
-----------------
Provides integration with financial data APIs for retrieving stock, crypto, and market data.
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


class FinanceProvider(DataProvider):
    """Finance data provider for retrieving financial market data."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for API key
        api_key = self.config.get('api_key') or os.getenv('FINANCE_API_KEY')
        if not api_key:
            raise ValueError("Finance API key is required. Set 'api_key' in config or FINANCE_API_KEY environment variable.")
        
        # Set default values
        self.config.setdefault('api_key', api_key)
        self.config.setdefault('base_url', self.config.get('base_url') or os.getenv('FINANCE_API_URL', 'https://financialmodelingprep.com/api/v3'))
        self.config.setdefault('timeout', int(os.getenv('FINANCE_API_TIMEOUT', '30')))
        self.config.setdefault('provider', self.config.get('provider') or os.getenv('FINANCE_API_PROVIDER', 'fmp'))
    
    def initialize(self) -> None:
        """Initialize the Finance API client."""
        try:
            # Initialize session when needed
            self.session = None
            
            logger.info(f"Initialized Finance API provider ({self.config['provider']}) with base URL: {self.config['base_url']}")
        except Exception as e:
            logger.error(f"Error initializing Finance API provider: {str(e)}")
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
        Query financial data based on a symbol or search query.
        
        Args:
            query: Symbol or search query
            **kwargs: Additional query parameters
            
        Returns:
            Query results
        """
        try:
            # Get session
            session = await self._get_session()
            
            # Determine query type
            query_type = kwargs.get('type', 'stock').lower()
            
            if query_type == 'search':
                return await self._search_symbols(query, **kwargs)
            elif query_type == 'stock':
                return await self._get_stock_data(query, **kwargs)
            elif query_type == 'crypto':
                return await self._get_crypto_data(query, **kwargs)
            elif query_type == 'forex':
                return await self._get_forex_data(query, **kwargs)
            elif query_type == 'market':
                return await self._get_market_data(query, **kwargs)
            else:
                raise ValueError(f"Unsupported query type: {query_type}")
        
        except Exception as e:
            logger.error(f"Error querying Finance API: {str(e)}")
            
            return {
                'success': False,
                'query': query,
                'error': str(e)
            }
    
    async def _search_symbols(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search for symbols based on a query."""
        session = await self._get_session()
        
        # Build URL and parameters
        url = f"{self.config['base_url']}/search"
        params = {
            'query': query,
            'limit': kwargs.get('limit', 10),
            'apikey': self.config['api_key']
        }
        
        async with session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Finance API returned status {response.status}: {error_text}")
            
            data = await response.json()
            
            return {
                'success': True,
                'query': query,
                'results': data,
                'metadata': {
                    'count': len(data),
                    'query_type': 'search'
                }
            }
    
    async def _get_stock_data(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Get stock data for a symbol."""
        session = await self._get_session()
        
        # Determine data type
        data_type = kwargs.get('data_type', 'quote').lower()
        
        if data_type == 'quote':
            url = f"{self.config['base_url']}/quote/{symbol}"
            params = {'apikey': self.config['api_key']}
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Finance API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                if not data:
                    return {
                        'success': False,
                        'query': symbol,
                        'error': f"No data found for symbol: {symbol}"
                    }
                
                return {
                    'success': True,
                    'query': symbol,
                    'data': data,
                    'metadata': {
                        'data_type': 'quote',
                        'symbol': symbol
                    }
                }
                
        elif data_type == 'profile':
            url = f"{self.config['base_url']}/profile/{symbol}"
            params = {'apikey': self.config['api_key']}
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Finance API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                if not data:
                    return {
                        'success': False,
                        'query': symbol,
                        'error': f"No profile data found for symbol: {symbol}"
                    }
                
                return {
                    'success': True,
                    'query': symbol,
                    'data': data,
                    'metadata': {
                        'data_type': 'profile',
                        'symbol': symbol
                    }
                }
                
        elif data_type == 'historical':
            url = f"{self.config['base_url']}/historical-price-full/{symbol}"
            
            params = {
                'apikey': self.config['api_key'],
                'serietype': 'line'
            }
            
            # Add date range if specified
            if 'from_date' in kwargs and 'to_date' in kwargs:
                params['from'] = kwargs['from_date']
                params['to'] = kwargs['to_date']
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Finance API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                if not data:
                    return {
                        'success': False,
                        'query': symbol,
                        'error': f"No historical data found for symbol: {symbol}"
                    }
                
                return {
                    'success': True,
                    'query': symbol,
                    'data': data,
                    'metadata': {
                        'data_type': 'historical',
                        'symbol': symbol,
                        'from_date': params.get('from'),
                        'to_date': params.get('to')
                    }
                }
                
        else:
            raise ValueError(f"Unsupported stock data type: {data_type}")
    
    async def _get_crypto_data(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Get cryptocurrency data for a symbol."""
        session = await self._get_session()
        
        # Determine data type
        data_type = kwargs.get('data_type', 'quote').lower()
        
        if data_type == 'quote':
            url = f"{self.config['base_url']}/quote/{symbol}USD"
            params = {'apikey': self.config['api_key']}
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Finance API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                if not data:
                    return {
                        'success': False,
                        'query': symbol,
                        'error': f"No data found for crypto: {symbol}"
                    }
                
                return {
                    'success': True,
                    'query': symbol,
                    'data': data,
                    'metadata': {
                        'data_type': 'quote',
                        'symbol': f"{symbol}USD",
                        'asset_type': 'crypto'
                    }
                }
                
        elif data_type == 'historical':
            url = f"{self.config['base_url']}/historical-price-full/crypto/{symbol}USD"
            
            params = {
                'apikey': self.config['api_key'],
                'serietype': 'line'
            }
            
            # Add date range if specified
            if 'from_date' in kwargs and 'to_date' in kwargs:
                params['from'] = kwargs['from_date']
                params['to'] = kwargs['to_date']
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Finance API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                if not data:
                    return {
                        'success': False,
                        'query': symbol,
                        'error': f"No historical data found for crypto: {symbol}"
                    }
                
                return {
                    'success': True,
                    'query': symbol,
                    'data': data,
                    'metadata': {
                        'data_type': 'historical',
                        'symbol': f"{symbol}USD",
                        'asset_type': 'crypto',
                        'from_date': params.get('from'),
                        'to_date': params.get('to')
                    }
                }
                
        else:
            raise ValueError(f"Unsupported crypto data type: {data_type}")
    
    async def _get_forex_data(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Get forex data for a currency pair."""
        # Implementation for forex data
        return {
            'success': False,
            'query': symbol,
            'error': "Forex data not implemented yet"
        }
    
    async def _get_market_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """Get market data based on query type."""
        session = await self._get_session()
        
        market_query = query.lower()
        
        if market_query == 'gainers':
            url = f"{self.config['base_url']}/stock_market/gainers"
            params = {'apikey': self.config['api_key']}
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Finance API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                return {
                    'success': True,
                    'query': 'gainers',
                    'data': data,
                    'metadata': {
                        'count': len(data),
                        'market_data_type': 'gainers'
                    }
                }
                
        elif market_query == 'losers':
            url = f"{self.config['base_url']}/stock_market/losers"
            params = {'apikey': self.config['api_key']}
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Finance API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                return {
                    'success': True,
                    'query': 'losers',
                    'data': data,
                    'metadata': {
                        'count': len(data),
                        'market_data_type': 'losers'
                    }
                }
                
        elif market_query == 'actives':
            url = f"{self.config['base_url']}/stock_market/actives"
            params = {'apikey': self.config['api_key']}
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Finance API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                return {
                    'success': True,
                    'query': 'actives',
                    'data': data,
                    'metadata': {
                        'count': len(data),
                        'market_data_type': 'actives'
                    }
                }
                
        elif market_query == 'sectors':
            url = f"{self.config['base_url']}/sector-performance"
            params = {'apikey': self.config['api_key']}
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Finance API returned status {response.status}: {error_text}")
                
                data = await response.json()
                
                return {
                    'success': True,
                    'query': 'sectors',
                    'data': data,
                    'metadata': {
                        'count': len(data),
                        'market_data_type': 'sectors'
                    }
                }
                
        else:
            raise ValueError(f"Unsupported market query: {market_query}. Supported queries: gainers, losers, actives, sectors")
    
    async def fetch(self, resource: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch a specific financial resource.
        
        Args:
            resource: Resource identifier (market_summary, crypto_list, etc.)
            **kwargs: Additional fetch parameters
            
        Returns:
            Resource data
        """
        try:
            # Get session
            session = await self._get_session()
            
            resource_type = resource.lower()
            
            if resource_type == 'market_summary':
                # Get market summary (multiple indices)
                url = f"{self.config['base_url']}/quotes/index"
                params = {'apikey': self.config['api_key']}
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Finance API returned status {response.status}: {error_text}")
                    
                    data = await response.json()
                    
                    return {
                        'success': True,
                        'resource': 'market_summary',
                        'data': data,
                        'metadata': {
                            'count': len(data),
                            'timestamp': datetime.now().isoformat()
                        }
                    }
                    
            elif resource_type == 'crypto_list':
                # Get list of available cryptocurrencies
                url = f"{self.config['base_url']}/symbol/available-cryptocurrencies"
                params = {'apikey': self.config['api_key']}
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Finance API returned status {response.status}: {error_text}")
                    
                    data = await response.json()
                    
                    return {
                        'success': True,
                        'resource': 'crypto_list',
                        'data': data,
                        'metadata': {
                            'count': len(data)
                        }
                    }
                    
            elif resource_type == 'stock_list':
                # Get list of available stocks
                url = f"{self.config['base_url']}/stock/list"
                params = {'apikey': self.config['api_key']}
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Finance API returned status {response.status}: {error_text}")
                    
                    data = await response.json()
                    
                    # Limit the response size
                    limit = kwargs.get('limit', 100)
                    data = data[:limit]
                    
                    return {
                        'success': True,
                        'resource': 'stock_list',
                        'data': data,
                        'metadata': {
                            'count': len(data),
                            'limit': limit
                        }
                    }
                    
            elif resource_type == 'earnings_calendar':
                # Get earnings calendar
                url = f"{self.config['base_url']}/earning-calendar"
                params = {'apikey': self.config['api_key']}
                
                # Add date range if specified
                if 'from_date' in kwargs:
                    params['from'] = kwargs['from_date']
                if 'to_date' in kwargs:
                    params['to'] = kwargs['to_date']
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Finance API returned status {response.status}: {error_text}")
                    
                    data = await response.json()
                    
                    return {
                        'success': True,
                        'resource': 'earnings_calendar',
                        'data': data,
                        'metadata': {
                            'count': len(data),
                            'from_date': params.get('from'),
                            'to_date': params.get('to')
                        }
                    }
                    
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")
        
        except Exception as e:
            logger.error(f"Error fetching finance resource: {str(e)}")
            
            return {
                'success': False,
                'resource': resource,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Finance API integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to check if the API is accessible
            loop = asyncio.get_event_loop()
            
            async def check():
                session = await self._get_session()
                
                # Try to fetch market index (lightweight request)
                url = f"{self.config['base_url']}/quotes/index"
                params = {'apikey': self.config['api_key']}
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return False, f"API returned status {response.status}"
                    
                    data = await response.json()
                    return len(data) > 0, "No data returned" if len(data) == 0 else None
            
            is_healthy, message = loop.run_until_complete(check())
            
            if is_healthy:
                return {
                    "status": "healthy",
                    "provider": "finance",
                    "api_provider": self.config['provider'],
                    "message": "API is accessible",
                    "details": {
                        "base_url": self.config['base_url']
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "finance",
                    "api_provider": self.config['provider'],
                    "error": message
                }
        
        except Exception as e:
            logger.error(f"Finance API health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "finance",
                "api_provider": self.config['provider'],
                "error": str(e)
            }