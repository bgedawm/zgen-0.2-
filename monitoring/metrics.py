"""
Metrics Monitoring System
--------------------
This module provides a metrics collection, storage, and visualization system
for monitoring the zgen AI Agent.
"""

import os
import time
import json
import threading
import datetime
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any, Union, Tuple, Callable

import logging
from logging.handlers import metrics_handler


class MetricsCollector:
    """
    A metrics collection system that gathers various metrics about the agent.
    """
    
    def __init__(self, storage_path='data/metrics'):
        """
        Initialize the metrics collector.
        
        Args:
            storage_path: Path to store metrics data
        """
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
        # Get a reference to the metrics handler from the logging system
        self.metrics_handler = self._get_metrics_handler()
        
        # Dictionary to store custom metrics
        self.custom_metrics = {}
        
        # Dictionary to store metric histories (for real-time monitoring)
        self.metric_histories = defaultdict(lambda: deque(maxlen=1000))
        
        # Dictionary to store metric callbacks
        self.metric_callbacks = {}
        
        # Lock for thread safety
        self.lock = threading.RLock()
    
    def _get_metrics_handler(self):
        """
        Get the metrics handler from the logging system.
        
        Returns:
            Metrics handler instance or None if not found
        """
        for handler in logging.getLogger().handlers:
            if isinstance(handler, metrics_handler.MetricsHandler):
                return handler
            
            # Check if it's a QueueHandler and has a metrics handler in its listeners
            if isinstance(handler, logging.handlers.QueueHandler):
                for listener in getattr(handler, 'handlers', []):
                    if isinstance(listener, metrics_handler.MetricsHandler):
                        return listener
        
        # If not found, create a new one
        handler = metrics_handler.MetricsHandler(
            storage_path=os.path.join(self.storage_path, 'logs'),
            save_interval=300,
            aggregation_interval=60,
            metrics_callback=self._metrics_callback
        )
        
        # Add it to the root logger
        logging.getLogger().addHandler(handler)
        
        return handler
    
    def _metrics_callback(self, metrics):
        """
        Callback for when metrics are aggregated.
        
        Args:
            metrics: Aggregated metrics
        """
        # Process metrics and update histories
        with self.lock:
            for timestamp, metric_data in metrics.items():
                for metric_name, values in metric_data.items():
                    if isinstance(values, dict) and 'avg' in values:
                        # Store the average value in the history
                        self.metric_histories[metric_name].append((timestamp, values['avg']))
                    else:
                        # Store the raw value in the history
                        self.metric_histories[metric_name].append((timestamp, values))
                    
                    # Call any registered callbacks for this metric
                    if metric_name in self.metric_callbacks:
                        try:
                            for callback in self.metric_callbacks[metric_name]:
                                callback(metric_name, values)
                        except Exception as e:
                            print(f"Error in metric callback for {metric_name}: {e}")
    
    def record_metric(self, name: str, value: Union[int, float], category: Optional[str] = None):
        """
        Record a custom metric.
        
        Args:
            name: Metric name
            value: Metric value
            category: Optional metric category
        """
        timestamp = time.time()
        
        with self.lock:
            # Store in custom metrics
            if category:
                metric_name = f"{category}.{name}"
            else:
                metric_name = name
            
            if metric_name not in self.custom_metrics:
                self.custom_metrics[metric_name] = []
            
            self.custom_metrics[metric_name].append((timestamp, value))
            
            # Store in metric history
            self.metric_histories[metric_name].append((
                datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                value
            ))
            
            # Call any registered callbacks
            if metric_name in self.metric_callbacks:
                for callback in self.metric_callbacks[metric_name]:
                    try:
                        callback(metric_name, value)
                    except Exception as e:
                        print(f"Error in metric callback for {metric_name}: {e}")
        
        # Also log the metric so it gets picked up by the metrics handler
        logging.getLogger('metrics').info(
            f"Metric: {metric_name}={value}",
            extra={
                'metric_name': metric_name,
                'metric_value': value,
                'metric_category': category
            }
        )
    
    def get_metric_history(self, metric_name: str, limit: int = 100) -> List[Tuple[str, Any]]:
        """
        Get the history of a metric.
        
        Args:
            metric_name: Metric name
            limit: Maximum number of entries to return
            
        Returns:
            List of (timestamp, value) tuples
        """
        with self.lock:
            history = list(self.metric_histories.get(metric_name, []))
            
            # Return the most recent entries
            return history[-limit:]
    
    def get_metric_average(self, metric_name: str, window_seconds: int = 60) -> Optional[float]:
        """
        Get the average value of a metric over a time window.
        
        Args:
            metric_name: Metric name
            window_seconds: Time window in seconds
            
        Returns:
            Average value or None if no data
        """
        with self.lock:
            history = list(self.metric_histories.get(metric_name, []))
            
            if not history:
                return None
            
            # Filter to the specified time window
            now = time.time()
            window_start = now - window_seconds
            
            # Filter values that are in the window
            window_values = []
            for timestamp_str, value in history:
                try:
                    # Convert timestamp string to unix time
                    timestamp = datetime.datetime.strptime(
                        timestamp_str, '%Y-%m-%d %H:%M:%S'
                    ).timestamp()
                    
                    if timestamp >= window_start:
                        if isinstance(value, dict) and 'avg' in value:
                            window_values.append(value['avg'])
                        else:
                            window_values.append(value)
                except:
                    pass
            
            if not window_values:
                return None
            
            # Calculate average
            return sum(window_values) / len(window_values)
    
    def get_all_metrics(self) -> Dict[str, List[Tuple[str, Any]]]:
        """
        Get all metric histories.
        
        Returns:
            Dictionary mapping metric names to their histories
        """
        with self.lock:
            return {
                name: list(history)
                for name, history in self.metric_histories.items()
            }
    
    def register_callback(self, metric_name: str, callback: Callable[[str, Any], None]):
        """
        Register a callback for a specific metric.
        
        Args:
            metric_name: Metric name
            callback: Callback function that takes the metric name and value
        """
        with self.lock:
            if metric_name not in self.metric_callbacks:
                self.metric_callbacks[metric_name] = []
            
            self.metric_callbacks[metric_name].append(callback)
    
    def unregister_callback(self, metric_name: str, callback: Callable[[str, Any], None]):
        """
        Unregister a callback for a specific metric.
        
        Args:
            metric_name: Metric name
            callback: Callback function to unregister
        """
        with self.lock:
            if metric_name in self.metric_callbacks:
                if callback in self.metric_callbacks[metric_name]:
                    self.metric_callbacks[metric_name].remove(callback)
    
    def save_metrics(self):
        """Save all metrics to disk."""
        if not self.custom_metrics:
            return
        
        with self.lock:
            # Get today's date for filename
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            filename = os.path.join(self.storage_path, f"custom-metrics-{today}.json")
            
            # Convert metrics to a format suitable for JSON
            metrics_json = {}
            for metric_name, values in self.custom_metrics.items():
                metrics_json[metric_name] = [
                    {
                        'timestamp': datetime.datetime.fromtimestamp(ts).isoformat(),
                        'value': value
                    }
                    for ts, value in values
                ]
            
            # Save to file
            with open(filename, 'w') as f:
                json.dump(metrics_json, f, indent=2)
    
    def get_errors(self) -> Dict[str, Any]:
        """
        Get all tracked errors.
        
        Returns:
            Dictionary of errors
        """
        if self.metrics_handler:
            return self.metrics_handler.get_errors()
        return {}


# Singleton instance
_metrics_collector = None

def get_metrics_collector():
    """
    Get the singleton metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_metric(name: str, value: Union[int, float], category: Optional[str] = None):
    """
    Record a custom metric.
    
    Args:
        name: Metric name
        value: Metric value
        category: Optional metric category
    """
    collector = get_metrics_collector()
    collector.record_metric(name, value, category)


def get_metric_history(metric_name: str, limit: int = 100) -> List[Tuple[str, Any]]:
    """
    Get the history of a metric.
    
    Args:
        metric_name: Metric name
        limit: Maximum number of entries to return
        
    Returns:
        List of (timestamp, value) tuples
    """
    collector = get_metrics_collector()
    return collector.get_metric_history(metric_name, limit)


def get_metric_average(metric_name: str, window_seconds: int = 60) -> Optional[float]:
    """
    Get the average value of a metric over a time window.
    
    Args:
        metric_name: Metric name
        window_seconds: Time window in seconds
        
    Returns:
        Average value or None if no data
    """
    collector = get_metrics_collector()
    return collector.get_metric_average(metric_name, window_seconds)


def get_all_metrics() -> Dict[str, List[Tuple[str, Any]]]:
    """
    Get all metric histories.
    
    Returns:
        Dictionary mapping metric names to their histories
    """
    collector = get_metrics_collector()
    return collector.get_all_metrics()


def register_callback(metric_name: str, callback: Callable[[str, Any], None]):
    """
    Register a callback for a specific metric.
    
    Args:
        metric_name: Metric name
        callback: Callback function that takes the metric name and value
    """
    collector = get_metrics_collector()
    collector.register_callback(metric_name, callback)


def unregister_callback(metric_name: str, callback: Callable[[str, Any], None]):
    """
    Unregister a callback for a specific metric.
    
    Args:
        metric_name: Metric name
        callback: Callback function to unregister
    """
    collector = get_metrics_collector()
    collector.unregister_callback(metric_name, callback)


def get_errors() -> Dict[str, Any]:
    """
    Get all tracked errors.
    
    Returns:
        Dictionary of errors
    """
    collector = get_metrics_collector()
    return collector.get_errors()