"""
Performance Monitoring
-----------------
This module provides performance monitoring for the zgen AI Agent,
tracking execution time, resource usage, and performance metrics for various components.
"""

import time
import functools
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Union

from monitoring.metrics import record_metric


class PerformanceTracker:
    """
    Tracks performance metrics for various operations.
    """
    
    def __init__(self, category=None):
        """
        Initialize the performance tracker.
        
        Args:
            category: Optional category for metrics
        """
        self.category = category
        self.logger = logging.getLogger('monitoring.performance')
    
    def track(self, name=None, log_level=logging.DEBUG):
        """
        Decorator for tracking the performance of a function.
        
        Args:
            name: Optional metric name (defaults to function name)
            log_level: Log level for performance logs
            
        Returns:
            Decorated function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                metric_name = name or func.__name__
                
                # Record start time
                start_time = time.time()
                
                # Execute the function
                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    success = False
                    raise
                finally:
                    # Record end time
                    end_time = time.time()
                    
                    # Calculate duration
                    duration = end_time - start_time
                    
                    # Record metric
                    full_name = f"{metric_name}_duration"
                    record_metric(full_name, duration, self.category or 'performance')
                    
                    # Record success/failure
                    outcome = 'success' if success else 'failure'
                    record_metric(f"{metric_name}_{outcome}", 1, self.category or 'performance')
                    
                    # Log execution time
                    self.logger.log(
                        log_level,
                        f"Function '{metric_name}' execution time: {duration:.4f} seconds",
                        extra={
                            'metric_name': full_name,
                            'metric_value': duration,
                            'function': metric_name,
                            'outcome': outcome
                        }
                    )
                
                return result
            
            return wrapper
        
        return decorator
    
    def track_async(self, name=None, log_level=logging.DEBUG):
        """
        Decorator for tracking the performance of an async function.
        
        Args:
            name: Optional metric name (defaults to function name)
            log_level: Log level for performance logs
            
        Returns:
            Decorated async function
        """
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                metric_name = name or func.__name__
                
                # Record start time
                start_time = time.time()
                
                # Execute the function
                try:
                    result = await func(*args, **kwargs)
                    success = True
                except Exception as e:
                    success = False
                    raise
                finally:
                    # Record end time
                    end_time = time.time()
                    
                    # Calculate duration
                    duration = end_time - start_time
                    
                    # Record metric
                    full_name = f"{metric_name}_duration"
                    record_metric(full_name, duration, self.category or 'performance')
                    
                    # Record success/failure
                    outcome = 'success' if success else 'failure'
                    record_metric(f"{metric_name}_{outcome}", 1, self.category or 'performance')
                    
                    # Log execution time
                    self.logger.log(
                        log_level,
                        f"Async function '{metric_name}' execution time: {duration:.4f} seconds",
                        extra={
                            'metric_name': full_name,
                            'metric_value': duration,
                            'function': metric_name,
                            'outcome': outcome
                        }
                    )
                
                return result
            
            return wrapper
        
        return decorator
    
    def track_context(self, name, log_level=logging.DEBUG):
        """
        Context manager for tracking the performance of a code block.
        
        Args:
            name: Metric name
            log_level: Log level for performance logs
            
        Returns:
            Context manager
        """
        return _PerformanceContext(name, log_level, self.category, self.logger)


class _PerformanceContext:
    """
    Context manager for tracking the performance of a code block.
    """
    
    def __init__(self, name, log_level, category, logger):
        """
        Initialize the performance context.
        
        Args:
            name: Metric name
            log_level: Log level for performance logs
            category: Metric category
            logger: Logger instance
        """
        self.name = name
        self.log_level = log_level
        self.category = category
        self.logger = logger
        self.start_time = None
    
    def __enter__(self):
        """Start tracking performance."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking performance and record metrics."""
        if self.start_time is None:
            return
        
        # Calculate duration
        end_time = time.time()
        duration = end_time - self.start_time
        
        # Record metric
        full_name = f"{self.name}_duration"
        record_metric(full_name, duration, self.category or 'performance')
        
        # Record success/failure
        outcome = 'failure' if exc_type else 'success'
        record_metric(f"{self.name}_{outcome}", 1, self.category or 'performance')
        
        # Log execution time
        self.logger.log(
            self.log_level,
            f"Block '{self.name}' execution time: {duration:.4f} seconds",
            extra={
                'metric_name': full_name,
                'metric_value': duration,
                'block': self.name,
                'outcome': outcome
            }
        )


# Default tracker instance
default_tracker = PerformanceTracker()

# Export decorator functions at module level
track = default_tracker.track
track_async = default_tracker.track_async
track_context = default_tracker.track_context


class PerformanceProfiler:
    """
    Profiles the performance of various components and operations.
    """
    
    def __init__(self):
        """Initialize the performance profiler."""
        self.trackers = {}
        self.logger = logging.getLogger('monitoring.profiler')
    
    def get_tracker(self, category):
        """
        Get a performance tracker for a specific category.
        
        Args:
            category: Tracker category
            
        Returns:
            PerformanceTracker instance
        """
        if category not in self.trackers:
            self.trackers[category] = PerformanceTracker(category)
        
        return self.trackers[category]
    
    def report_stats(self, category=None):
        """
        Report performance statistics for the given category.
        
        Args:
            category: Optional category filter
            
        Returns:
            Dictionary with performance statistics
        """
        from monitoring.metrics import get_all_metrics
        
        metrics = get_all_metrics()
        
        # Filter metrics by category
        if category:
            category_prefix = f"{category}."
            filtered_metrics = {}
            for name, values in metrics.items():
                if name.startswith(category_prefix):
                    simplified_name = name[len(category_prefix):]
                    filtered_metrics[simplified_name] = values
        else:
            # Just use metrics with 'performance' category
            filtered_metrics = {}
            for name, values in metrics.items():
                if name.startswith('performance.'):
                    simplified_name = name[len('performance.'):]
                    filtered_metrics[simplified_name] = values
        
        return filtered_metrics


# Singleton instance
_profiler = None

def get_profiler():
    """
    Get the singleton performance profiler instance.
    
    Returns:
        PerformanceProfiler instance
    """
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler()
    return _profiler


def get_tracker(category):
    """
    Get a performance tracker for a specific category.
    
    Args:
        category: Tracker category
        
    Returns:
        PerformanceTracker instance
    """
    profiler = get_profiler()
    return profiler.get_tracker(category)


def report_stats(category=None):
    """
    Report performance statistics for the given category.
    
    Args:
        category: Optional category filter
        
    Returns:
        Dictionary with performance statistics
    """
    profiler = get_profiler()
    return profiler.report_stats(category)