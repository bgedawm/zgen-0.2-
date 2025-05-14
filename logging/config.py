"""
Logging Configuration
--------------------
This module provides a centralized logging configuration for the zgen AI Agent.
It sets up logging handlers, formatters, and log rotation.
"""

import os
import sys
import yaml
import logging
import logging.config
from pathlib import Path
from typing import Dict, Any, Optional

# Import enhanced logging functionality
from logging.logger import setup_logging as _setup_enhanced_logging
from logging.logger import get_logger, TaskLogger, ApiLogger, SystemLogger


def configure_logging(
    config_path: Optional[str] = None,
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True,
    use_json: bool = False,
    use_colors: bool = True,
    capture_stdout: bool = False,
    metrics_enabled: bool = True
) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        config_path: Path to logging YAML configuration file
        log_level: Default log level if not using config file
        log_file: Path to log file
        console: Whether to log to console
        use_json: Whether to use JSON format for logs
        use_colors: Whether to use colors in console output
        capture_stdout: Whether to capture stdout/stderr
        metrics_enabled: Whether to enable metrics collection from logs
        
    Returns:
        The root logger
    """
    # If config file exists, use it
    if config_path and os.path.exists(config_path):
        return _configure_from_file(config_path)
    
    # Otherwise, use the enhanced logging setup
    return _setup_enhanced_logging(
        level=log_level,
        log_file=log_file,
        use_json=use_json,
        use_colors=use_colors,
        log_to_console=console,
        capture_stdout=capture_stdout,
        metrics_enabled=metrics_enabled
    )


def _configure_from_file(config_path: str) -> logging.Logger:
    """
    Configure logging from a YAML file.
    
    Args:
        config_path: Path to logging configuration YAML file
        
    Returns:
        The root logger
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Create log directories if they don't exist
        for handler_config in config.get('handlers', {}).values():
            if 'filename' in handler_config:
                log_dir = os.path.dirname(handler_config['filename'])
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)
        
        logging.config.dictConfig(config)
        
        # Get and return the root logger
        logger = logging.getLogger()
        logger.info(f"Logging configured from {config_path}")
        return logger
    
    except Exception as e:
        # Fall back to basic configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        logger = logging.getLogger()
        logger.error(f"Error configuring logging from {config_path}: {e}")
        logger.info("Falling back to basic logging configuration")
        return logger


def get_task_logger(task_id: str, context: Optional[Dict[str, Any]] = None) -> TaskLogger:
    """
    Get a task-specific logger.
    
    Args:
        task_id: Task ID
        context: Additional context information
        
    Returns:
        Task logger
    """
    return TaskLogger(task_id, context)


def get_api_logger() -> ApiLogger:
    """
    Get an API logger.
    
    Returns:
        API logger
    """
    return ApiLogger()


def get_system_logger() -> SystemLogger:
    """
    Get a system logger.
    
    Returns:
        System logger
    """
    return SystemLogger()


# Export our wrapper functions and the enhanced logging functions
__all__ = [
    'configure_logging',
    'get_logger',
    'get_task_logger',
    'get_api_logger',
    'get_system_logger',
    'TaskLogger',
    'ApiLogger',
    'SystemLogger'
]