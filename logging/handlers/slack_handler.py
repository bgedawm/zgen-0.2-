"""
Slack Notification Handler
--------------------
This module provides a handler for sending critical log messages
to Slack channels or users.
"""

import os
import json
import logging
import time
import requests
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set


class SlackNotificationHandler(logging.Handler):
    """
    A handler that sends log messages to Slack.
    
    This handler batches messages and has rate limiting to avoid
    overwhelming the Slack API.
    """
    
    def __init__(
        self,
        webhook_url=None,
        token=None,
        channel=None,
        username=None,
        icon_emoji=None,
        rate_limit=5,  # messages per minute
        batch_size=5,   # messages per batch
        batch_interval=60,  # seconds between batches
        notify_levels=None  # log levels to notify (default: ERROR and above)
    ):
        """
        Initialize the Slack notification handler.
        
        Args:
            webhook_url: Slack webhook URL
            token: Slack API token
            channel: Slack channel or user to send messages to
            username: Username to use for messages
            icon_emoji: Emoji to use as the icon
            rate_limit: Maximum number of messages per minute
            batch_size: Maximum number of messages per batch
            batch_interval: Time between batches in seconds
            notify_levels: List of log levels to notify about
        """
        super().__init__()
        
        # Get configuration from environment variables if not provided
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        self.token = token or os.getenv('SLACK_API_TOKEN')
        self.channel = channel or os.getenv('SLACK_CHANNEL')
        self.username = username or os.getenv('SLACK_USERNAME', 'zgen Agent')
        self.icon_emoji = icon_emoji or os.getenv('SLACK_ICON_EMOJI', ':robot_face:')
        
        # Validate configuration
        if not self.webhook_url and not self.token:
            raise ValueError("Either Slack webhook URL or API token is required")
        
        if not self.webhook_url and not self.channel:
            raise ValueError("Channel is required when using Slack API token")
        
        # Set notification levels
        if notify_levels is None:
            self.notify_levels = {logging.ERROR, logging.CRITICAL}
        else:
            self.notify_levels = set(notify_levels)
        
        # Rate limiting and batching settings
        self.rate_limit = max(1, rate_limit)  # at least 1 per minute
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        
        # Message queue and rate limiting state
        self.message_queue = []
        self.message_times = []
        self.queue_lock = threading.RLock()
        
        # Start the batch processing thread
        self.batch_thread = threading.Thread(
            target=self._batch_sender,
            name="SlackHandler-BatchSender",
            daemon=True
        )
        self.batch_thread.start()
        
        # Keep track of recently sent message hashes to avoid duplicates
        self.recent_messages = set()
        self.max_recent = 100
    
    def emit(self, record):
        """
        Queue a log record for sending to Slack.
        
        Args:
            record: Log record to send
        """
        if record.levelno not in self.notify_levels:
            return
        
        try:
            # Format the record
            message = self.format(record)
            
            # Create a hash of the message to avoid duplicates
            message_hash = hash(message[:100])  # Use first 100 chars for hash
            
            with self.queue_lock:
                # Check for duplicates
                if message_hash in self.recent_messages:
                    return
                
                # Add to recent messages
                self.recent_messages.add(message_hash)
                if len(self.recent_messages) > self.max_recent:
                    self.recent_messages.pop()
                
                # Add to queue
                self.message_queue.append(self._prepare_message(record, message))
                
                # Check if we need to send immediately
                if record.levelno >= logging.CRITICAL or len(self.message_queue) >= self.batch_size:
                    # Create a background thread to send right away
                    threading.Thread(
                        target=self._process_queue,
                        name="SlackHandler-ImmediateSend",
                        daemon=True
                    ).start()
        
        except Exception:
            self.handleError(record)
    
    def _prepare_message(self, record, formatted_message):
        """
        Prepare a message for sending to Slack.
        
        Args:
            record: Log record
            formatted_message: Formatted log message
            
        Returns:
            Dictionary with prepared message
        """
        # Get timestamp
        timestamp = datetime.fromtimestamp(record.created).isoformat()
        
        # Determine color based on log level
        color_map = {
            logging.DEBUG: '#3498db',    # Blue
            logging.INFO: '#2ecc71',     # Green
            logging.WARNING: '#f39c12',  # Yellow
            logging.ERROR: '#e74c3c',    # Red
            logging.CRITICAL: '#9b59b6'  # Purple
        }
        color = color_map.get(record.levelno, '#95a5a6')  # Default: Gray
        
        # Create the attachment
        attachment = {
            'fallback': formatted_message,
            'color': color,
            'title': f"{record.levelname}: {record.name}",
            'text': formatted_message,
            'fields': [
                {
                    'title': 'Logger',
                    'value': record.name,
                    'short': True
                },
                {
                    'title': 'Level',
                    'value': record.levelname,
                    'short': True
                }
            ],
            'ts': record.created
        }
        
        # Add exception info if present
        if record.exc_info:
            attachment['fields'].append({
                'title': 'Exception',
                'value': self._format_exception(record.exc_info),
                'short': False
            })
        
        # Add extra fields from the record
        for key, value in record.__dict__.items():
            # Skip standard keys and internal Python attributes
            if (key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 
                           'filename', 'funcName', 'id', 'levelname', 'levelno', 
                           'lineno', 'module', 'msecs', 'message', 'msg', 
                           'name', 'pathname', 'process', 'processName', 
                           'relativeCreated', 'stack_info', 'thread', 'threadName') and
                not key.startswith('_')):
                
                # Convert value to string if needed
                if not isinstance(value, (str, int, float, bool, type(None))):
                    if isinstance(value, (dict, list)):
                        try:
                            value = json.dumps(value)
                        except:
                            value = str(value)
                    else:
                        value = str(value)
                
                # Add as a field
                attachment['fields'].append({
                    'title': key,
                    'value': value,
                    'short': len(str(value)) < 50  # Short if the value is short
                })
        
        return {
            'attachments': [attachment],
            'username': self.username,
            'icon_emoji': self.icon_emoji,
            'channel': self.channel,
            'timestamp': timestamp
        }
    
    def _format_exception(self, exc_info):
        """
        Format an exception for display in Slack.
        
        Args:
            exc_info: Exception info tuple
            
        Returns:
            Formatted exception string
        """
        import traceback
        exc_type, exc_value, exc_tb = exc_info
        return f"```{exc_type.__name__}: {exc_value}\n{''.join(traceback.format_tb(exc_tb))}```"
    
    def _batch_sender(self):
        """Background thread that periodically processes the message queue."""
        while True:
            # Sleep for the batch interval
            time.sleep(self.batch_interval)
            
            # Process the queue
            self._process_queue()
    
    def _process_queue(self):
        """Process the message queue, respecting rate limits."""
        with self.queue_lock:
            # Check if there are messages to send
            if not self.message_queue:
                return
            
            # Enforce rate limit
            now = time.time()
            self.message_times = [t for t in self.message_times if now - t < 60]
            
            # If we're at the rate limit, don't send now
            if len(self.message_times) >= self.rate_limit:
                return
            
            # Calculate how many messages we can send
            available_slots = min(self.rate_limit - len(self.message_times), len(self.message_queue))
            
            if available_slots <= 0:
                return
            
            # Take messages from the queue
            messages = self.message_queue[:available_slots]
            self.message_queue = self.message_queue[available_slots:]
            
            # Update rate limit tracking
            for _ in range(len(messages)):
                self.message_times.append(now)
        
        # Send messages
        for msg in messages:
            self._send_message(msg)
    
    def _send_message(self, message):
        """
        Send a message to Slack.
        
        Args:
            message: Prepared message dictionary
        """
        try:
            if self.webhook_url:
                # Use webhook
                data = {
                    'attachments': message['attachments'],
                    'username': message['username'],
                    'icon_emoji': message['icon_emoji']
                }
                
                if message.get('channel'):
                    data['channel'] = message['channel']
                
                response = requests.post(
                    self.webhook_url,
                    json=data,
                    timeout=10
                )
                
                if response.status_code != 200:
                    print(f"Error sending Slack notification: {response.status_code} {response.text}")
            
            elif self.token:
                # Use Slack API
                headers = {
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json; charset=utf-8'
                }
                
                data = {
                    'attachments': message['attachments'],
                    'username': message['username'],
                    'icon_emoji': message['icon_emoji'],
                    'channel': message['channel']
                }
                
                response = requests.post(
                    'https://slack.com/api/chat.postMessage',
                    headers=headers,
                    json=data,
                    timeout=10
                )
                
                if response.status_code != 200 or not response.json().get('ok'):
                    print(f"Error sending Slack notification: {response.status_code} {response.text}")
        
        except Exception as e:
            print(f"Error sending Slack notification: {str(e)}")
    
    def close(self):
        """Close the handler and process any remaining messages."""
        # Process any remaining messages in the queue
        self._process_queue()
        
        # Call the parent close method
        super().close()