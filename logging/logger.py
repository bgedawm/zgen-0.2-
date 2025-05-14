"""
Enhanced Logging System
-------------------
This module provides an enhanced logging configuration for the zgen AI Agent.
It includes structured logging, multiple output formats, and integration with
monitoring systems.
"""

import os
import sys
import json
import time
import logging
import logging.handlers
import atexit
import threading
import queue
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Callable

# Import formatters and handlers
from logging.formatters import (
    structured_formatter,
    json_formatter,
    colored_formatter
)
from logging.handlers import (
    async_handler,
    rotating_file_handler,
    slack_handler, 
    metrics_handler
)

# Default log directory
LOG_DIR = Path("data/logs")

# Global log queue for async logging
log_queue = queue.Queue(-1)  # No limit on size
log_listener = None
log_listener_thread = None


def setup_logging(
    level=logging.INFO,
    log_file=None,
    use_json=False,
    use_colors=True,
    backup_count=10,
    max_bytes=50*1024*1024,  # 50MB
    notify_errors=False,
    capture_stdout=False,
    metrics_enabled=True,
    log_to_console=True
):
    """
    Set up enhanced logging for the application.
    
    Args:
        level: The logging level (default: INFO)
        log_file: Path to the log file (default: None, will be auto-generated)
        use_json: Whether to use JSON format for log files (default: False)
        use_colors: Whether to use colors in console output (default: True)
        backup_count: Number of log files to keep (default: 10)
        max_bytes: Maximum size of each log file in bytes (default: 50MB)
        notify_errors: Whether to send notifications for errors (default: False)
        capture_stdout: Whether to capture stdout and stderr (default: False)
        metrics_enabled: Whether to collect metrics from logs (default: True)
        log_to_console: Whether to log to console (default: True)
    
    Returns:
        The root logger
    """
    global log_listener, log_listener_thread
    
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (LOG_DIR / "tasks").mkdir(exist_ok=True)
    (LOG_DIR / "system").mkdir(exist_ok=True)
    (LOG_DIR / "api").mkdir(exist_ok=True)
    (LOG_DIR / "errors").mkdir(exist_ok=True)
    
    # Generate log filename if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = LOG_DIR / f"zgen-{timestamp}.log"
    
    # Convert string level to logging level
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicate logs
    root_logger.handlers = []
    
    # Start the log listener thread for async logging
    log_listener = logging.handlers.QueueListener(
        log_queue, respect_handler_level=True
    )
    
    # Create formatters
    if use_json:
        main_formatter = json_formatter.JsonFormatter()
    else:
        main_formatter = structured_formatter.StructuredFormatter()
    
    # Console formatter with colors if enabled
    if use_colors:
        console_formatter = colored_formatter.ColoredFormatter()
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # Create handlers and add them to the listener
    
    # Main log file (all logs)
    main_handler = rotating_file_handler.EnhancedRotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    main_handler.setLevel(level)
    main_handler.setFormatter(main_formatter)
    log_listener.handlers.append(main_handler)
    
    # Error log file (ERROR and above)
    error_log_file = LOG_DIR / "errors" / f"errors-{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = rotating_file_handler.EnhancedRotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(main_formatter)
    log_listener.handlers.append(error_handler)
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        log_listener.handlers.append(console_handler)
    
    # Add notification handler for errors if enabled
    if notify_errors:
        notify_handler = slack_handler.SlackNotificationHandler()
        notify_handler.setLevel(logging.ERROR)
        log_listener.handlers.append(notify_handler)
    
    # Add metrics handler if enabled
    if metrics_enabled:
        metrics_handler_instance = metrics_handler.MetricsHandler()
        metrics_handler_instance.setLevel(logging.INFO)
        log_listener.handlers.append(metrics_handler_instance)
    
    # Start the listener
    log_listener.start()
    
    # Create the queue handler that all loggers will use
    queue_handler = logging.handlers.QueueHandler(log_queue)
    root_logger.addHandler(queue_handler)
    
    # Capture stdout and stderr if requested
    if capture_stdout:
        sys.stdout = _StdoutCapturer('STDOUT')
        sys.stderr = _StdoutCapturer('STDERR')
    
    # Register cleanup on exit
    atexit.register(_cleanup_logging)
    
    # Log the start of the logging system
    root_logger.info(f"Enhanced logging initialized (level: {logging.getLevelName(level)})")
    root_logger.info(f"Main log file: {log_file}")
    root_logger.info(f"Error log file: {error_log_file}")
    
    return root_logger


def get_logger(name, extra_data=None):
    """
    Get a logger with the specified name and optional extra data.
    
    Args:
        name: The logger name
        extra_data: Optional extra data to include in all log records
        
    Returns:
        A logger instance
    """
    logger = logging.getLogger(name)
    
    if extra_data:
        return _LoggerAdapter(logger, extra_data)
    
    return logger


class _LoggerAdapter(logging.LoggerAdapter):
    """Adapter that adds extra context data to log records."""
    
    def process(self, msg, kwargs):
        # Ensure extra dict exists
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Add our extra data
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs


class TaskLogger:
    """A specialized logger for tracking task execution."""
    
    def __init__(self, task_id, context=None):
        """
        Initialize a task logger.
        
        Args:
            task_id: The unique ID of the task
            context: Optional context information about the task
        """
        self.task_id = task_id
        self.context = context or {}
        
        # Add task_id to context
        self.context['task_id'] = task_id
        
        # Initialize metrics
        self.start_time = time.time()
        self.step_times = {}
        self.current_step = None
        self.step_start_time = None
        
        # Create a logger with the task context
        self.logger = get_logger(f"task.{task_id}", self.context)
        
        # Create a task-specific log file
        log_file = LOG_DIR / "tasks" / f"{task_id}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a file handler for this task
        formatter = structured_formatter.StructuredFormatter()
        file_handler = async_handler.AsyncFileHandler(log_file)
        file_handler.setFormatter(formatter)
        
        # Add the handler directly to the logger (bypass queue for task-specific logs)
        self.logger.addHandler(file_handler)
        
        # Log task start
        self.info(f"Task started: {task_id}")
    
    def info(self, message, **kwargs):
        """Log an info message."""
        if kwargs:
            self.logger.info(message, extra=kwargs)
        else:
            self.logger.info(message)
    
    def error(self, message, exc_info=None, **kwargs):
        """Log an error message."""
        if exc_info is True:
            if kwargs:
                self.logger.error(message, exc_info=True, extra=kwargs)
            else:
                self.logger.error(message, exc_info=True)
        elif exc_info:
            if kwargs:
                self.logger.error(message, extra=dict(kwargs, exc_info=str(exc_info), 
                                                    traceback=traceback.format_exc()))
            else:
                self.logger.error(message, extra={'exc_info': str(exc_info), 
                                                'traceback': traceback.format_exc()})
        else:
            if kwargs:
                self.logger.error(message, extra=kwargs)
            else:
                self.logger.error(message)
    
    def warning(self, message, **kwargs):
        """Log a warning message."""
        if kwargs:
            self.logger.warning(message, extra=kwargs)
        else:
            self.logger.warning(message)
    
    def debug(self, message, **kwargs):
        """Log a debug message."""
        if kwargs:
            self.logger.debug(message, extra=kwargs)
        else:
            self.logger.debug(message)
    
    def start_step(self, step_name):
        """
        Start timing a task step.
        
        Args:
            step_name: Name of the step
        """
        if self.current_step:
            self.end_step()
            
        self.current_step = step_name
        self.step_start_time = time.time()
        self.info(f"Starting step: {step_name}")
    
    def end_step(self):
        """End timing the current step."""
        if self.current_step and self.step_start_time:
            duration = time.time() - self.step_start_time
            self.step_times[self.current_step] = duration
            
            self.info(f"Finished step: {self.current_step}", 
                     duration=duration,
                     step=self.current_step)
            
            self.current_step = None
            self.step_start_time = None
    
    def log_metric(self, name, value, unit=None):
        """
        Log a custom metric.
        
        Args:
            name: Metric name
            value: Metric value
            unit: Optional unit of measurement
        """
        self.info(f"Metric: {name} = {value}{f' {unit}' if unit else ''}",
                 metric_name=name,
                 metric_value=value,
                 metric_unit=unit)
    
    def get_logs(self, max_lines=100, include_timestamps=True):
        """
        Retrieve the latest logs for the task.
        
        Args:
            max_lines: Maximum number of lines to retrieve
            include_timestamps: Whether to include timestamps
            
        Returns:
            List of log entries
        """
        log_file = LOG_DIR / "tasks" / f"{self.task_id}.log"
        if not log_file.exists():
            return []
        
        with open(log_file, "r") as f:
            # Get the last N lines
            lines = f.readlines()
            filtered_lines = lines[-max_lines:] if max_lines > 0 else lines
            
            if not include_timestamps:
                # Strip timestamps if requested
                filtered_lines = [l.split(" - ", 1)[1] if " - " in l else l for l in filtered_lines]
            
            return filtered_lines
    
    def get_metrics(self):
        """
        Get task metrics.
        
        Returns:
            Dictionary with task metrics
        """
        total_duration = time.time() - self.start_time
        
        metrics = {
            'task_id': self.task_id,
            'duration': total_duration,
            'steps': self.step_times.copy()
        }
        
        return metrics
    
    def finish(self, status='completed', result=None, error=None):
        """
        Finish the task and log completion details.
        
        Args:
            status: Completion status ('completed', 'failed', etc.)
            result: Optional result information
            error: Optional error information
        """
        # End any ongoing step
        if self.current_step:
            self.end_step()
        
        # Calculate total duration
        duration = time.time() - self.start_time
        
        # Log completion
        if status == 'failed' and error:
            self.error(f"Task failed: {self.task_id}", 
                      duration=duration,
                      error=str(error))
        else:
            self.info(f"Task {status}: {self.task_id}",
                     duration=duration,
                     status=status,
                     result=result)
        
        # Return metrics
        return self.get_metrics()


class ApiLogger:
    """A specialized logger for API requests."""
    
    def __init__(self):
        """Initialize the API logger."""
        self.logger = get_logger("api")
        
        # Create API log file
        log_file = LOG_DIR / "api" / f"api-{datetime.now().strftime('%Y%m%d')}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a file handler for API logs
        formatter = json_formatter.JsonFormatter()
        file_handler = async_handler.AsyncFileHandler(log_file)
        file_handler.setFormatter(formatter)
        
        # Add the handler directly to the logger
        self.logger.addHandler(file_handler)
    
    def log_request(self, method, path, params=None, body=None, user_id=None, client_ip=None):
        """
        Log an API request.
        
        Args:
            method: HTTP method
            path: Request path
            params: Optional query parameters
            body: Optional request body
            user_id: Optional user ID
            client_ip: Optional client IP address
        """
        self.logger.info(
            f"API Request: {method} {path}",
            extra={
                'event_type': 'api_request',
                'http_method': method,
                'path': path,
                'params': params,
                'body': body,
                'user_id': user_id,
                'client_ip': client_ip,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def log_response(self, method, path, status_code, response_time, response_size=None, error=None):
        """
        Log an API response.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            response_time: Response time in seconds
            response_size: Optional response size in bytes
            error: Optional error message
        """
        self.logger.info(
            f"API Response: {method} {path} - {status_code}",
            extra={
                'event_type': 'api_response',
                'http_method': method,
                'path': path,
                'status_code': status_code,
                'response_time': response_time,
                'response_size': response_size,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
        )


class SystemLogger:
    """A specialized logger for system events."""
    
    def __init__(self):
        """Initialize the system logger."""
        self.logger = get_logger("system")
        
        # Add metrics collector for system metrics
        self.metrics = {}
        
        # Create system log file
        log_file = LOG_DIR / "system" / f"system-{datetime.now().strftime('%Y%m%d')}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a file handler for system logs
        formatter = structured_formatter.StructuredFormatter()
        file_handler = async_handler.AsyncFileHandler(log_file)
        file_handler.setFormatter(formatter)
        
        # Add the handler directly to the logger
        self.logger.addHandler(file_handler)
    
    def log_startup(self, config=None):
        """
        Log system startup.
        
        Args:
            config: Optional configuration details
        """
        self.logger.info(
            "System starting up",
            extra={
                'event_type': 'system_startup',
                'config': config,
                'timestamp': datetime.now().isoformat(),
                'python_version': sys.version
            }
        )
    
    def log_shutdown(self, reason=None):
        """
        Log system shutdown.
        
        Args:
            reason: Optional shutdown reason
        """
        self.logger.info(
            "System shutting down",
            extra={
                'event_type': 'system_shutdown',
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def log_config_change(self, setting, old_value, new_value, user=None):
        """
        Log a configuration change.
        
        Args:
            setting: Setting that was changed
            old_value: Previous value
            new_value: New value
            user: Optional user who made the change
        """
        self.logger.info(
            f"Configuration changed: {setting}",
            extra={
                'event_type': 'config_change',
                'setting': setting,
                'old_value': old_value,
                'new_value': new_value,
                'user': user,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def log_resource_usage(self, cpu_percent, memory_percent, disk_usage=None, network_io=None):
        """
        Log system resource usage.
        
        Args:
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            disk_usage: Optional disk usage statistics
            network_io: Optional network I/O statistics
        """
        self.logger.info(
            f"Resource usage: CPU {cpu_percent}%, Memory {memory_percent}%",
            extra={
                'event_type': 'resource_usage',
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_usage': disk_usage,
                'network_io': network_io,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Update metrics
        self.metrics['cpu_percent'] = cpu_percent
        self.metrics['memory_percent'] = memory_percent
        if disk_usage:
            self.metrics['disk_usage'] = disk_usage
        if network_io:
            self.metrics['network_io'] = network_io
    
    def log_error(self, message, component=None, error_type=None, exc_info=None, stack_trace=None):
        """
        Log a system error.
        
        Args:
            message: Error message
            component: Optional component where the error occurred
            error_type: Optional error type
            exc_info: Optional exception info
            stack_trace: Optional stack trace
        """
        if exc_info is True:
            self.logger.error(
                f"System error: {message}",
                exc_info=True,
                extra={
                    'event_type': 'system_error',
                    'component': component,
                    'error_type': error_type,
                    'timestamp': datetime.now().isoformat()
                }
            )
        else:
            if not stack_trace and exc_info:
                stack_trace = traceback.format_exception(
                    type(exc_info), exc_info, exc_info.__traceback__
                )
            
            self.logger.error(
                f"System error: {message}",
                extra={
                    'event_type': 'system_error',
                    'component': component,
                    'error_type': error_type,
                    'exc_info': str(exc_info) if exc_info else None,
                    'stack_trace': stack_trace,
                    'timestamp': datetime.now().isoformat()
                }
            )
    
    def get_metrics(self):
        """
        Get collected system metrics.
        
        Returns:
            Dictionary with system metrics
        """
        return self.metrics.copy()


class _StdoutCapturer:
    """Captures stdout/stderr output and logs it."""
    
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger(f"stdout.{name.lower()}")
        self.buffer = []
    
    def write(self, text):
        # Only process if there's actual text
        if text and text.strip():
            # If text doesn't end with a newline, buffer it
            if not text.endswith('\n'):
                self.buffer.append(text)
                return
            
            # If we have buffered text, combine it
            if self.buffer:
                text = ''.join(self.buffer) + text
                self.buffer = []
            
            # Log each line separately
            for line in text.rstrip('\n').split('\n'):
                if line.strip():  # Skip empty lines
                    self.logger.info(line)
            
            # Also write to the original stdout/stderr
            if self.name == 'STDOUT':
                sys.__stdout__.write(text)
            else:
                sys.__stderr__.write(text)
    
    def flush(self):
        # Flush any remaining buffered content
        if self.buffer:
            text = ''.join(self.buffer)
            if text.strip():
                self.logger.info(text)
            self.buffer = []
        
        # Flush the original stdout/stderr
        if self.name == 'STDOUT':
            sys.__stdout__.flush()
        else:
            sys.__stderr__.flush()


def _cleanup_logging():
    """Clean up logging resources on exit."""
    global log_listener, log_listener_thread
    
    if log_listener:
        log_listener.stop()
        log_listener = None
        
    if log_listener_thread and log_listener_thread.is_alive():
        log_listener_thread.join(1.0)  # Wait up to 1 second
        log_listener_thread = None
    
    # Revert stdout/stderr if they were captured
    if isinstance(sys.stdout, _StdoutCapturer):
        sys.stdout = sys.__stdout__
    
    if isinstance(sys.stderr, _StdoutCapturer):
        sys.stderr = sys.__stderr__