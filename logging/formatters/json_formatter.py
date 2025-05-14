"""
JSON Log Formatter
--------------
This module provides a formatter that outputs logs in JSON format
for easy parsing by log analysis tools.
"""

import json
import logging
import datetime
import socket
import os
import traceback
from typing import Dict, Any, Optional


class JsonFormatter(logging.Formatter):
    """
    A formatter that produces JSON formatted log messages.
    """
    
    def __init__(self, include_process_info=True, include_thread_info=True, indent=None):
        """
        Initialize the JSON formatter.
        
        Args:
            include_process_info: Whether to include process information
            include_thread_info: Whether to include thread information
            indent: Indentation level for JSON (None for no indentation)
        """
        super().__init__()
        self.include_process_info = include_process_info
        self.include_thread_info = include_thread_info
        self.indent = indent
        
        # Host and process information (static)
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.app_name = os.getenv('APP_NAME', 'zgen')
    
    def format(self, record):
        """
        Format the log record into a JSON string.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log message
        """
        # Extract the base message
        message = record.getMessage()
        
        # Start with common fields
        output = {
            '@timestamp': self.format_time(record),
            'level': record.levelname,
            'logger': record.name,
            'message': message,
            'app': self.app_name,
            'host': self.hostname
        }
        
        # Add process info if requested
        if self.include_process_info:
            output['process'] = {
                'id': self.pid,
                'name': record.processName
            }
        
        # Add thread info if requested
        if self.include_thread_info:
            output['thread'] = {
                'id': record.thread,
                'name': record.threadName
            }
            
        # Add location info
        output['log'] = {
            'origin': {
                'file': {
                    'name': record.filename,
                    'path': record.pathname,
                    'line': record.lineno
                },
                'function': record.funcName
            }
        }
        
        # Add exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            
            output['error'] = {
                'type': exc_type.__name__,
                'message': str(exc_value),
                'stacktrace': self.format_traceback(exc_traceback)
            }
        elif record.exc_text:
            output['error'] = {
                'message': record.exc_text
            }
        
        # Add any extra attributes from the record
        if hasattr(record, 'extra'):
            for key, value in record.extra.items():
                # Handle fields that might conflict with existing ones
                if key in output and isinstance(output[key], dict) and isinstance(value, dict):
                    # Merge dictionaries
                    output[key].update(value)
                else:
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
        
        # Convert to JSON
        return json.dumps(output, default=self._json_serializer, indent=self.indent)
    
    def format_time(self, record):
        """
        Format the timestamp from the record.
        
        Args:
            record: Log record
            
        Returns:
            ISO formatted timestamp
        """
        dt = datetime.datetime.fromtimestamp(record.created)
        return dt.isoformat()
    
    def format_traceback(self, tb):
        """
        Format a traceback into a list of strings.
        
        Args:
            tb: Traceback object
            
        Returns:
            Formatted traceback string
        """
        if tb:
            return ''.join(traceback.format_tb(tb))
        return None
    
    def _json_serializer(self, obj):
        """
        Custom JSON serializer for objects not serializable by default.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Serializable version of the object
        
        Raises:
            TypeError: If object cannot be serialized
        """
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        
        if isinstance(obj, datetime.timedelta):
            return str(obj)
        
        if isinstance(obj, set):
            return list(obj)
        
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        
        # Let the default serializer raise the TypeError
        raise TypeError(f"Type {type(obj)} not serializable")