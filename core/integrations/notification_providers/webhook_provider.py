"""
Webhook Notification Provider
------------------------
Provides integration with custom webhooks for notifications.
"""

import os
import logging
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional

from ..base import NotificationProvider

# Setup logger
logger = logging.getLogger(__name__)


class WebhookProvider(NotificationProvider):
    """Webhook notification provider."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for webhook URL
        webhook_url = self.config.get('webhook_url') or os.getenv('WEBHOOK_URL')
        if not webhook_url:
            raise ValueError("Webhook URL is required. Set 'webhook_url' in config or WEBHOOK_URL environment variable.")
        
        # Set default values
        self.config.setdefault('webhook_url', webhook_url)
        self.config.setdefault('method', os.getenv('WEBHOOK_METHOD', 'POST'))
        self.config.setdefault('headers', {})
        self.config.setdefault('timeout', int(os.getenv('WEBHOOK_TIMEOUT', '30')))
        
        # Add custom headers from environment variables
        webhook_headers = os.getenv('WEBHOOK_HEADERS', '')
        if webhook_headers:
            try:
                import json
                headers = json.loads(webhook_headers)
                self.config['headers'].update(headers)
            except Exception as e:
                logger.warning(f"Failed to parse WEBHOOK_HEADERS: {str(e)}")
    
    def initialize(self) -> None:
        """Initialize the webhook client."""
        try:
            # Initialize session when needed
            self.session = None
            
            logger.info(f"Initialized webhook notification provider: {self.config['webhook_url']}")
        except Exception as e:
            logger.error(f"Error initializing webhook provider: {str(e)}")
            raise
    
    async def _get_session(self):
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config['timeout']),
                headers=self.config['headers']
            )
        return self.session
    
    async def send_notification(self, 
                               message: str, 
                               title: Optional[str] = None, 
                               level: str = "info", 
                               recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send a notification via webhook.
        
        Args:
            message: Notification message
            title: Optional notification title
            level: Notification level (info, warning, error, success)
            recipients: Optional list of recipients (not used for webhooks)
            
        Returns:
            Dictionary with send status
        """
        try:
            # Prepare payload
            payload = {
                "message": message,
                "level": level
            }
            
            if title:
                payload["title"] = title
            
            # Add timestamp
            import datetime
            payload["timestamp"] = datetime.datetime.now().isoformat()
            
            # Get session
            session = await self._get_session()
            
            # Send request
            method = self.config['method'].upper()
            url = self.config['webhook_url']
            
            if method == 'GET':
                # For GET requests, parameters are sent as query parameters
                async with session.get(url, params=payload) as response:
                    if response.status not in (200, 201, 202, 204):
                        error_text = await response.text()
                        raise Exception(f"Webhook returned status {response.status}: {error_text}")
                    
                    response_data = {}
                    try:
                        response_data = await response.json()
                    except:
                        response_data = {"text": await response.text()}
                    
                    return {
                        "success": True,
                        "provider": "webhook",
                        "response": response_data
                    }
            else:
                # For other methods, send as JSON payload
                async with session.request(method, url, json=payload) as response:
                    if response.status not in (200, 201, 202, 204):
                        error_text = await response.text()
                        raise Exception(f"Webhook returned status {response.status}: {error_text}")
                    
                    response_data = {}
                    try:
                        response_data = await response.json()
                    except:
                        response_data = {"text": await response.text()}
                    
                    return {
                        "success": True,
                        "provider": "webhook",
                        "response": response_data
                    }
        
        except Exception as e:
            logger.error(f"Error sending webhook notification: {str(e)}")
            
            return {
                "success": False,
                "provider": "webhook",
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the webhook integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to check if the webhook is accessible
            loop = asyncio.get_event_loop()
            
            async def check():
                # Send a test notification
                result = await self.send_notification(
                    message="Health check test notification",
                    title="Health Check",
                    level="info"
                )
                return result
            
            result = loop.run_until_complete(check())
            
            if result.get("success", False):
                return {
                    "status": "healthy",
                    "provider": "webhook",
                    "details": {
                        "url": self.config['webhook_url'],
                        "method": self.config['method']
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "webhook",
                    "error": result.get("error", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Webhook health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "webhook",
                "error": str(e)
            }