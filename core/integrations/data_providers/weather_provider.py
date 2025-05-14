"""
Weather Data Provider
-----------------
Provides integration with weather data APIs.
"""

import os
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from ..base import DataProvider

# Setup logger
logger = logging.getLogger(__name__)


class WeatherProvider(DataProvider):
    """Weather data provider using OpenWeatherMap API by default."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # API key is required
        api_key = self.config.get('api_key') or os.getenv('WEATHER_API_KEY')
        if not api_key:
            raise ValueError("Weather API key is required. Set 'api_key' in config or WEATHER_API_KEY environment variable.")
        
        # Set default values
        self.config.setdefault('api_key', api_key)
        self.config.setdefault('service', os.getenv('WEATHER_SERVICE', 'openweathermap'))
        self.config.setdefault('timeout', int(os.getenv('WEATHER_TIMEOUT', '30')))
        self.config.setdefault('units', os.getenv('WEATHER_UNITS', 'metric'))
        self.config.setdefault('language', os.getenv('WEATHER_LANGUAGE', 'en'))
        
        # Set API endpoints based on service
        if self.config['service'] == 'openweathermap':
            self.config.setdefault('base_url', 'https://api.openweathermap.org/data/2.5/')
        elif self.config['service'] == 'weatherapi':
            self.config.setdefault('base_url', 'https://api.weatherapi.com/v1/')
        elif self.config['service'] == 'accuweather':
            self.config.setdefault('base_url', 'https://dataservice.accuweather.com/')
        else:
            # Custom service
            base_url = self.config.get('base_url') or os.getenv('WEATHER_BASE_URL')
            if not base_url:
                raise ValueError(f"Base URL is required for custom service '{self.config['service']}'")
            self.config.setdefault('base_url', base_url)
    
    def initialize(self) -> None:
        """Initialize the weather provider."""
        try:
            # Initialize session when needed
            self.session = None
            
            logger.info(f"Initialized weather provider using {self.config['service']}")
        except Exception as e:
            logger.error(f"Error initializing weather provider: {str(e)}")
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
        Query weather data.
        
        Args:
            query: The query string (city name, coordinates, etc.)
            **kwargs: Additional query parameters
            
        Returns:
            Weather data
        """
        try:
            # Determine the endpoint based on service and query type
            endpoint = self._get_endpoint(query, **kwargs)
            
            # Prepare query parameters
            params = self._prepare_params(query, **kwargs)
            
            # Get session
            session = await self._get_session()
            
            # Make request
            url = urljoin(self.config['base_url'], endpoint)
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "status": response.status,
                        "error": error_text
                    }
                
                data = await response.json()
                
                # Process response based on service
                processed_data = self._process_response(data, **kwargs)
                
                return {
                    "success": True,
                    "status": response.status,
                    "data": processed_data
                }
        
        except Exception as e:
            logger.error(f"Error querying weather data: {str(e)}")
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_endpoint(self, query: str, **kwargs) -> str:
        """
        Get the appropriate API endpoint based on the query type.
        
        Args:
            query: The query string
            **kwargs: Additional parameters
            
        Returns:
            API endpoint
        """
        service = self.config['service']
        query_type = kwargs.get('type', 'current')
        
        if service == 'openweathermap':
            if query_type == 'current':
                return 'weather'
            elif query_type == 'forecast':
                return 'forecast'
            elif query_type == 'onecall':
                return 'onecall'
            else:
                return 'weather'
        
        elif service == 'weatherapi':
            if query_type == 'current':
                return 'current.json'
            elif query_type == 'forecast':
                return 'forecast.json'
            else:
                return 'current.json'
        
        elif service == 'accuweather':
            if query_type == 'current':
                return 'currentconditions/v1/'
            elif query_type == 'forecast':
                return 'forecasts/v1/daily/5day/'
            else:
                return 'currentconditions/v1/'
        
        # Custom service - use the provided endpoint or default
        return kwargs.get('endpoint', 'weather')
    
    def _prepare_params(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Prepare query parameters based on the service.
        
        Args:
            query: The query string
            **kwargs: Additional parameters
            
        Returns:
            Query parameters
        """
        service = self.config['service']
        params = {}
        
        if service == 'openweathermap':
            # Check if query looks like coordinates
            if ',' in query and all(part.replace('.', '').replace('-', '').isdigit() for part in query.split(',')):
                lat, lon = query.split(',')
                params['lat'] = lat.strip()
                params['lon'] = lon.strip()
            else:
                params['q'] = query
            
            params['appid'] = self.config['api_key']
            params['units'] = self.config['units']
            params['lang'] = self.config['language']
        
        elif service == 'weatherapi':
            params['key'] = self.config['api_key']
            params['q'] = query
            params['lang'] = self.config['language']
            
            if kwargs.get('type') == 'forecast':
                params['days'] = kwargs.get('days', 3)
            
            if self.config['units'] == 'imperial':
                params['units'] = 'f'  # Fahrenheit
        
        elif service == 'accuweather':
            # AccuWeather requires location key, so we need to fetch it first if not provided
            if kwargs.get('location_key'):
                params['locationKey'] = kwargs.get('location_key')
            else:
                # Will need to handle this in the query method
                params['q'] = query
            
            params['apikey'] = self.config['api_key']
            params['language'] = self.config['language']
            
            if self.config['units'] == 'metric':
                params['metric'] = 'true'
        
        else:
            # Custom service - add API key and query
            api_key_param = kwargs.get('api_key_param', 'apikey')
            query_param = kwargs.get('query_param', 'q')
            
            params[api_key_param] = self.config['api_key']
            params[query_param] = query
            
            # Add units and language if specified
            if 'units_param' in kwargs and 'units' in self.config:
                params[kwargs['units_param']] = self.config['units']
            
            if 'language_param' in kwargs and 'language' in self.config:
                params[kwargs['language_param']] = self.config['language']
        
        # Add any additional parameters
        for key, value in kwargs.items():
            if key not in ('type', 'endpoint', 'api_key_param', 'query_param', 'units_param', 'language_param'):
                params[key] = value
        
        return params
    
    def _process_response(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Process the API response based on the service.
        
        Args:
            data: Raw API response data
            **kwargs: Additional parameters
            
        Returns:
            Processed weather data
        """
        service = self.config['service']
        query_type = kwargs.get('type', 'current')
        
        # For simplicity, return the raw data
        # In a real implementation, you would normalize the data from different services
        return data
    
    async def fetch(self, resource: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch weather data for a specific location.
        
        Args:
            resource: Location identifier (city name, coordinates, etc.)
            **kwargs: Additional parameters
            
        Returns:
            Weather data
        """
        # This is an alias for query in this provider
        return await self.query(resource, **kwargs)
    
    async def get_current_weather(self, location: str) -> Dict[str, Any]:
        """
        Get current weather for a location.
        
        Args:
            location: Location identifier (city name, coordinates, etc.)
            
        Returns:
            Current weather data
        """
        return await self.query(location, type='current')
    
    async def get_forecast(self, location: str, days: int = 5) -> Dict[str, Any]:
        """
        Get weather forecast for a location.
        
        Args:
            location: Location identifier (city name, coordinates, etc.)
            days: Number of days for forecast
            
        Returns:
            Forecast data
        """
        return await self.query(location, type='forecast', days=days)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the weather provider.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Try to get weather for a known location
            loop = asyncio.get_event_loop()
            
            async def check():
                result = await self.get_current_weather("London")
                return result
            
            result = loop.run_until_complete(check())
            
            if result.get("success", False):
                return {
                    "status": "healthy",
                    "provider": "weather",
                    "service": self.config['service'],
                    "details": {
                        "units": self.config['units'],
                        "language": self.config['language']
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "weather",
                    "service": self.config['service'],
                    "error": result.get("error", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Weather provider health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "weather",
                "service": self.config['service'],
                "error": str(e)
            }