"""
Discord Notification Provider
------------------------
Provides integration with Discord for notifications.
"""

import os
import logging
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
import datetime

from ..base import NotificationProvider

# Setup logger
logger = logging.getLogger(__name__)


class DiscordProvider(NotificationProvider):
    """Discord notification provider."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for webhook URL
        webhook_url = self.config.get('webhook_url') or os.getenv('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            raise ValueError("Discord webhook URL is required. Set 'webhook_url' in config or DISCORD_WEBHOOK_URL environment variable.")
        
        # Set default values
        self.config.setdefault('webhook_url', webhook_url)
        self.config.setdefault('username', self.config.get('username') or os.getenv('DISCORD_USERNAME', 'Scout Agent'))
        self.config.setdefault('avatar_url', self.config.get('avatar_url') or os.getenv('DISCORD_AVATAR_URL'))
        self.config.setdefault('timeout', int(os.getenv('DISCORD_TIMEOUT', '30')))
    
    def initialize(self) -> None:
        """Initialize the Discord client."""
        try:
            # Initialize session when needed
            self.session = None
            
            logger.info(f"Initialized Discord notification provider")
        except Exception as e:
            logger.error(f"Error initializing Discord provider: {str(e)}")
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
        Send a notification via Discord.
        
        Args:
            message: Notification message
            title: Optional notification title
            level: Notification level (info, warning, error, success)
            recipients: Optional list of recipients (webhook URLs)
            
        Returns:
            Dictionary with send status
        """
        try:
            # Determine color based on level
            color_map = {
                "info": 0x3498db,     # Blue
                "success": 0x2ecc71,  # Green
                "warning": 0xf39c12,  # Orange
                "error": 0xe74c3c     # Red
            }
            color = color_map.get(level.lower(), 0x3498db)
            
            # Create Discord message payload
            payload = {
                "username": self.config['username'],
                "content": "",
                "embeds": [
                    {
                        "title": title if title else f"{level.capitalize()} Notification",
                        "description": message,
                        "color": color,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                ]
            }
            
            # Add avatar URL if provided
            if self.config['avatar_url']:
                payload["avatar_url"] = self.config['avatar_url']
            
            # Get session
            session = await self._get_session()
            
            # Determine webhook URLs
            webhook_urls = []
            if recipients:
                webhook_urls = recipients
            else:
                webhook_urls = [self.config['webhook_url']]
            
            # Send to each webhook URL
            results = []
            
            for webhook_url in webhook_urls:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status not in (200, 201, 204):
                        error_text = await response.text()
                        results.append({
                            "webhook": webhook_url,
                            "success": False,
                            "error": f"Discord webhook returned status {response.status}: {error_text}"
                        })
                    else:
                        results.append({
                            "webhook": webhook_url,
                            "success": True
                        })
            
            # Check if all messages were sent successfully
            all_success = all(result["success"] for result in results)
            
            return {
                "success": all_success,
                "provider": "discord",
                "results": results
            }
        
        except Exception as e:
            logger.error(f"Error sending Discord notification: {str(e)}")
            
            return {
                "success": False,
                "provider": "discord",
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Discord integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to check if the webhook is accessible
            loop = asyncio.get_event_loop()
            
            async def check():
                session = await self._get_session()
                
                # Test webhook with minimal payload
                payload = {
                    "content": "Health check",
                    "username": self.config['username']
                }
                
                async with session.post(self.config['webhook_url'], json=payload) as response:
                    if response.status not in (200, 201, 204):
                        error_text = await response.text()
                        raise Exception(f"Discord webhook returned status {response.status}: {error_text}")
                    
                    return True
            
            is_healthy = loop.run_until_complete(check())
            
            if is_healthy:
                return {
                    "status": "healthy",
                    "provider": "discord",
                    "details": {
                        "username": self.config['username']
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "discord",
                    "error": "Failed to send test notification"
                }
        
        except Exception as e:
            logger.error(f"Discord health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "discord",
                "error": str(e)
            }