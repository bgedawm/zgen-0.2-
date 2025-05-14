"""
Slack Notification Provider
----------------------
Provides integration with Slack for notifications.
"""

import os
import logging
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional

from ..base import NotificationProvider

# Setup logger
logger = logging.getLogger(__name__)


class SlackProvider(NotificationProvider):
    """Slack notification provider."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for webhook URL or token
        webhook_url = self.config.get('webhook_url') or os.getenv('SLACK_WEBHOOK_URL')
        token = self.config.get('token') or os.getenv('SLACK_API_TOKEN')
        
        if not webhook_url and not token:
            raise ValueError("Either Slack webhook URL or API token is required.")
        
        # Set default values
        self.config.setdefault('webhook_url', webhook_url)
        self.config.setdefault('token', token)
        self.config.setdefault('channel', self.config.get('channel') or os.getenv('SLACK_CHANNEL'))
        self.config.setdefault('username', self.config.get('username') or os.getenv('SLACK_USERNAME', 'Scout Agent'))
        self.config.setdefault('icon_emoji', self.config.get('icon_emoji') or os.getenv('SLACK_ICON_EMOJI', ':robot_face:'))
        self.config.setdefault('timeout', int(os.getenv('SLACK_TIMEOUT', '30')))
    
    def initialize(self) -> None:
        """Initialize the Slack client."""
        try:
            # Initialize session when needed
            self.session = None
            
            # Determine the API mode: webhook or token
            self.api_mode = 'webhook' if self.config['webhook_url'] else 'token'
            
            if self.api_mode == 'token' and not self.config['channel']:
                logger.warning("No default Slack channel specified. Channel must be provided for each notification.")
            
            logger.info(f"Initialized Slack notification provider (mode: {self.api_mode})")
        except Exception as e:
            logger.error(f"Error initializing Slack provider: {str(e)}")
            raise
    
    async def _get_session(self):
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_mode == 'token':
                headers['Authorization'] = f"Bearer {self.config['token']}"
            
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config['timeout']),
                headers=headers
            )
        return self.session
    
    async def send_notification(self, 
                               message: str, 
                               title: Optional[str] = None, 
                               level: str = "info", 
                               recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send a notification via Slack.
        
        Args:
            message: Notification message
            title: Optional notification title
            level: Notification level (info, warning, error, success)
            recipients: Optional list of recipients (channels or users)
            
        Returns:
            Dictionary with send status
        """
        try:
            # Determine color based on level
            color_map = {
                "info": "#3498db",
                "success": "#2ecc71",
                "warning": "#f39c12",
                "error": "#e74c3c"
            }
            color = color_map.get(level.lower(), "#3498db")
            
            # Create Slack message payload
            blocks = []
            
            if title:
                # Add header block
                blocks.append({
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title,
                        "emoji": True
                    }
                })
            
            # Add message block
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            })
            
            # Add context block with timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Level:* {level.capitalize()} | *Time:* {timestamp}"
                    }
                ]
            })
            
            # Add divider
            blocks.append({"type": "divider"})
            
            # Get session
            session = await self._get_session()
            
            # Determine recipients
            channels = []
            if recipients:
                channels = recipients
            elif self.config['channel']:
                channels = [self.config['channel']]
            else:
                # If no recipients and no default channel, fail
                raise ValueError("No Slack channel specified. Provide recipients or set default channel.")
            
            # Send to each recipient
            results = []
            
            for channel in channels:
                if self.api_mode == 'webhook':
                    # Use webhook
                    payload = {
                        "blocks": blocks,
                        "username": self.config['username'],
                        "icon_emoji": self.config['icon_emoji']
                    }
                    
                    async with session.post(self.config['webhook_url'], json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"Slack webhook returned status {response.status}: {error_text}")
                        
                        response_text = await response.text()
                        
                        results.append({
                            "channel": "webhook",
                            "success": response_text == "ok",
                            "response": response_text
                        })
                else:
                    # Use API token
                    payload = {
                        "channel": channel,
                        "blocks": blocks,
                        "username": self.config['username'],
                        "icon_emoji": self.config['icon_emoji']
                    }
                    
                    async with session.post("https://slack.com/api/chat.postMessage", json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"Slack API returned status {response.status}: {error_text}")
                        
                        response_data = await response.json()
                        
                        results.append({
                            "channel": channel,
                            "success": response_data.get("ok", False),
                            "response": response_data
                        })
            
            # Check if all messages were sent successfully
            all_success = all(result["success"] for result in results)
            
            return {
                "success": all_success,
                "provider": "slack",
                "results": results
            }
        
        except Exception as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            
            return {
                "success": False,
                "provider": "slack",
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Slack integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to check if Slack is accessible
            loop = asyncio.get_event_loop()
            
            async def check():
                session = await self._get_session()
                
                if self.api_mode == 'webhook':
                    # Test webhook with minimal payload
                    payload = {
                        "text": "Health check",
                        "username": self.config['username']
                    }
                    
                    async with session.post(self.config['webhook_url'], json=payload) as response:
                        if response.status != 200:
                            raise Exception(f"Slack webhook returned status {response.status}")
                        
                        response_text = await response.text()
                        return response_text == "ok"
                else:
                    # Test API token
                    async with session.get("https://slack.com/api/auth.test") as response:
                        if response.status != 200:
                            raise Exception(f"Slack API returned status {response.status}")
                        
                        response_data = await response.json()
                        return response_data.get("ok", False)
            
            is_healthy = loop.run_until_complete(check())
            
            if is_healthy:
                return {
                    "status": "healthy",
                    "provider": "slack",
                    "mode": self.api_mode,
                    "details": {
                        "username": self.config['username'],
                        "default_channel": self.config.get('channel')
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "slack",
                    "mode": self.api_mode,
                    "error": "Authentication failed"
                }
        
        except Exception as e:
            logger.error(f"Slack health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "slack",
                "mode": self.api_mode,
                "error": str(e)
            }