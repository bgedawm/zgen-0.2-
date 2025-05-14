"""
Logging Utility
--------------
This module provides a centralized logging configuration for the Local Scout AI Agent.
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

# Default log directory
LOG_DIR = Path("data/logs")


def setup_logging(level=logging.INFO, log_file=None):
    """
    Set up logging for the application.
    
    Args:
        level: The logging level (default: INFO)
        log_file: Path to the log file (default: None, will be auto-generated)
    """
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = LOG_DIR / f"scout-{timestamp}.log"
    
    # Convert string level to logging level
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicate logs
    root_logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Log the start of the logging system
    root_logger.info(f"Logging initialized (level: {logging.getLevelName(level)})")
    root_logger.info(f"Log file: {log_file}")
    
    return root_logger


def get_logger(name):
    """
    Get a logger with the specified name.
    
    Args:
        name: The logger name
        
    Returns:
        A logger instance
    """
    return logging.getLogger(name)


class TaskLogger:
    """A specialized logger for tracking task execution."""
    
    def __init__(self, task_id):
        """
        Initialize a task logger.
        
        Args:
            task_id: The unique ID of the task
        """
        self.task_id = task_id
        self.logger = logging.getLogger(f"task.{task_id}")
        
        # Create a task-specific log file
        log_file = LOG_DIR / "tasks" / f"{task_id}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a file handler for this task
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        
        # Add the handler to this logger
        self.logger.addHandler(file_handler)
    
    def info(self, message):
        """Log an info message."""
        self.logger.info(message)
    
    def error(self, message):
        """Log an error message."""
        self.logger.error(message)
    
    def warning(self, message):
        """Log a warning message."""
        self.logger.warning(message)
    
    def debug(self, message):
        """Log a debug message."""
        self.logger.debug(message)
    
    def get_logs(self, max_lines=100):
        """
        Retrieve the latest logs for the task.
        
        Args:
            max_lines: Maximum number of lines to retrieve
            
        Returns:
            List of log entries
        """
        log_file = LOG_DIR / "tasks" / f"{self.task_id}.log"
        if not log_file.exists():
            return []
        
        with open(log_file, "r") as f:
            # Get the last N lines
            lines = f.readlines()
            return lines[-max_lines:] if max_lines > 0 else lines