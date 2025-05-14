"""
Structured Log Formatter
--------------------
This module provides a formatter that outputs logs in a structured format
with consistent fields.
"""

import logging
import datetime
import socket
import os
import sys
import traceback
import json
from typing import Dict, Any, Optional


class StructuredFormatter(logging.Formatter):
    """
    A formatter that produces structured log messages with consistent fields.
    """
    
    def __init__(self, include_process_info=True, include_thread_info=True):
        """
        Initialize the structured formatter.
        
        Args:
            include_process_info: Whether to include process information
            include_thread_info: Whether to include thread information
        """
        super().__init__()
        self.include_process_info = include_process_info
        self.include_thread_info = include_thread_info
        
        # Host and process information (static)
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.app_name = os.getenv('APP_NAME', 'zgen')
    
    def format(self, record):
        """
        Format the log record into a structured string.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log message
        """
        # Extract the base message
        message = record.getMessage()
        
        # Start with common fields
        output = {
            'timestamp': self.format_time(record),
            'level': record.levelname,
            'logger': record.name,
            'message': message,
            'app': self.app_name,
            'host': self.hostname
        }
        
        # Add process info if requested
        if self.include_process_info:
            output['pid'] = self.pid
        
        # Add thread info if requested
        if self.include_thread_info:
            output['thread'] = record.threadName
            
        # Add location info
        output['location'] = f"{record.pathname}:{record.lineno}"
        
        # Add exception info if present
        if record.exc_info:
            output['exception'] = {
                'type': record.exc_info[0].__name__,
                'value': str(record.exc_info[1]),
                'traceback': self.format_traceback(record.exc_info[2])
            }
        elif record.exc_text:
            output['exception'] = record.exc_text
        
        # Add any extra attributes from the record
        if hasattr(record, 'extra'):
            for key, value in record.extra.items():
                if key not in output:
                    output[key] = value
        
        # Add any other custom attributes from the record
        for key, value in record.__dict__.items():
            if (key not in output and 
                key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 
                           'filename', 'funcName', 'id', 'levelno', 'lineno', 
                           'module', 'msecs', 'msg', 'name', 'pathname', 
                           'process', 'processName', 'relativeCreated', 
                           'stack_info', 'thread', 'threadName')):
                output[key] = value
        
        # Format as a structured string (not JSON)
        parts = []
        for key, value in output.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            parts.append(f"{key}={self._format_value(value)}")
        
        return ' | '.join(parts)
    
    def format_time(self, record):
        """
        Format the timestamp from the record.
        
        Args:
            record: Log record
            
        Returns:
            Formatted timestamp
        """
        dt = datetime.datetime.fromtimestamp(record.created)
        return dt.isoformat(timespec='milliseconds')
    
    def format_traceback(self, tb):
        """
        Format a traceback into a list of strings.
        
        Args:
            tb: Traceback object
            
        Returns:
            List of traceback lines
        """
        return traceback.format_tb(tb)
    
    def _format_value(self, value):
        """
        Format a value for inclusion in the structured log.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted value
        """
        if value is None:
            return 'null'
        
        if isinstance(value, bool):
            return str(value).lower()
        
        if isinstance(value, (int, float)):
            return str(value)
        
        if isinstance(value, str):
            # Escape quotes and wrap in quotes if the value contains spaces or special chars
            if ' ' in value or '|' in value or '=' in value or '"' in value or "'" in value:
                return f'"{value.replace('"', '\\"')}"'
            return value
        
        # For any other type, just convert to string
        return str(value)