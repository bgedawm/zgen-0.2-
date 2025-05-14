"""
Pushover Notification Provider
-------------------------
Provides integration with Pushover for mobile notifications.
"""

import os
import logging
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional

from ..base import NotificationProvider

# Setup logger
logger = logging.getLogger(__name__)


class PushoverProvider(NotificationProvider):
    """Pushover notification provider."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for API token and user key
        token = self.config.get('token') or os.getenv('PUSHOVER_TOKEN')
        if not token:
            raise ValueError("Pushover API token is required. Set 'token' in config or PUSHOVER_TOKEN environment variable.")
        
        user = self.config.get('user') or os.getenv('PUSHOVER_USER')
        if not user:
            raise ValueError("Pushover user key is required. Set 'user' in config or PUSHOVER_USER environment variable.")
        
        # Set default values
        self.config.setdefault('token', token)
        self.config.setdefault('user', user)
        self.config.setdefault('device', self.config.get('device') or os.getenv('PUSHOVER_DEVICE'))
        self.config.setdefault('timeout', int(os.getenv('PUSHOVER_TIMEOUT', '30')))
        self.config.setdefault('api_url', 'https://api.pushover.net/1/messages.json')
    
    def initialize(self) -> None:
        """Initialize the Pushover client."""
        try:
            # Initialize session when needed
            self.session = None
            
            logger.info(f"Initialized Pushover notification provider")
        except Exception as e:
            logger.error(f"Error initializing Pushover provider: {str(e)}")
            raise
    
    async def _get_session(self):
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config['timeout'])
            )
        return self.session
    
    async def send_notification(self, 
                               message: str, 
                               title: Optional[str] = None, 
                               level: str = "info", 
                               recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send a notification via Pushover.
        
        Args:
            message: Notification message
            title: Optional notification title
            level: Notification level (info, warning, error, success)
            recipients: Optional list of recipients (user keys)
            
        Returns:
            Dictionary with send status
        """
        try:
            # Map level to Pushover priority
            priority_map = {
                "info": 0,         # Normal priority
                "success": 0,      # Normal priority
                "warning": 1,      # High priority
                "error": 2         # Emergency priority
            }
            priority = priority_map.get(level.lower(), 0)
            
            # Create Pushover payload
            payload = {
                "token": self.config['token'],
                "message": message,
                "priority": priority
            }
            
            # Add title if provided
            if title:
                payload["title"] = title
            
            # Add device if configured
            if self.config['device']:
                payload["device"] = self.config['device']
            
            # Add sound based on level
            sound_map = {
                "info": "pushover",
                "success": "magic",
                "warning": "bike",
                "error": "siren"
            }
            payload["sound"] = sound_map.get(level.lower(), "pushover")
            
            # For emergency priority, require acknowledgement
            if priority == 2:
                payload["retry"] = 60  # Retry every 60 seconds
                payload["expire"] = 3600  # Expire after 1 hour
            
            # Get session
            session = await self._get_session()
            
            # Determine recipients
            users = []
            if recipients:
                users = recipients
            else:
                users = [self.config['user']]
            
            # Send to each recipient
            results = []
            
            for user in users:
                # Update user key for this recipient
                payload["user"] = user
                
                async with session.post(self.config['api_url'], data=payload) as response:
                    response_data = await response.json()
                    
                    if response.status != 200 or response_data.get("status") != 1:
                        results.append({
                            "user": user,
                            "success": False,
                            "error": response_data.get("errors", ["Unknown error"])[0] if "errors" in response_data else "Unknown error"
                        })
                    else:
                        results.append({
                            "user": user,
                            "success": True,
                            "request_id": response_data.get("request")
                        })
            
            # Check if all notifications were sent successfully
            all_success = all(result["success"] for result in results)
            
            return {
                "success": all_success,
                "provider": "pushover",
                "results": results
            }
        
        except Exception as e:
            logger.error(f"Error sending Pushover notification: {str(e)}")
            
            return {
                "success": False,
                "provider": "pushover",
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Pushover integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to validate API token and user key
            loop = asyncio.get_event_loop()
            
            async def check():
                session = await self._get_session()
                
                # Use validate endpoint to check token and user
                validate_url = 'https://api.pushover.net/1/users/validate.json'
                payload = {
                    "token": self.config['token'],
                    "user": self.config['user']
                }
                
                if self.config['device']:
                    payload["device"] = self.config['device']
                
                async with session.post(validate_url, data=payload) as response:
                    response_data = await response.json()
                    
                    if response.status != 200 or response_data.get("status") != 1:
                        error = response_data.get("errors", ["Unknown error"])[0] if "errors" in response_data else "Unknown error"
                        raise Exception(f"Pushover validation failed: {error}")
                    
                    return response_data
            
            validation = loop.run_until_complete(check())
            
            return {
                "status": "healthy",
                "provider": "pushover",
                "details": {
                    "devices": validation.get("devices", []),
                    "device": self.config.get('device')
                }
            }
        
        except Exception as e:
            logger.error(f"Pushover health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "pushover",
                "error": str(e)
            }