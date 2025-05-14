"""
Metrics Logging Handler
------------------
This module provides a logging handler that extracts metrics from log messages
for monitoring and visualization.
"""

import os
import re
import time
import logging
import threading
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, Any, List, Optional, Set, Tuple, Union


class MetricsHandler(logging.Handler):
    """
    A handler that extracts metrics from log messages for monitoring.
    """
    
    # Regex patterns for common metrics in log messages
    PATTERNS = {
        'duration': re.compile(r'duration[=:]\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
        'size': re.compile(r'size[=:]\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
        'count': re.compile(r'count[=:]\s*(\d+)', re.IGNORECASE),
        'memory': re.compile(r'memory[=:]\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
        'cpu': re.compile(r'cpu[=:]\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
        'latency': re.compile(r'latency[=:]\s*(\d+(?:\.\d+)?)', re.IGNORECASE)
    }
    
    def __init__(
        self,
        storage_path=None,
        save_interval=300,  # Save metrics every 5 minutes
        aggregation_interval=60,  # Aggregate metrics every 1 minute
        custom_metrics=None,  # Additional metrics to extract
        metrics_callback=None  # Callback for when metrics are aggregated
    ):
        """
        Initialize the metrics handler.
        
        Args:
            storage_path: Path to store metrics data
            save_interval: Interval in seconds for saving metrics to disk
            aggregation_interval: Interval in seconds for aggregating metrics
            custom_metrics: Additional regex patterns for custom metrics
            metrics_callback: Callback function for when metrics are aggregated
        """
        super().__init__()
        
        # Storage path
        self.storage_path = storage_path or os.getenv('METRICS_STORAGE_PATH', 'data/metrics')
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Intervals
        self.save_interval = save_interval
        self.aggregation_interval = aggregation_interval
        
        # Metrics callback
        self.metrics_callback = metrics_callback
        
        # Add custom metrics patterns
        if custom_metrics:
            for name, pattern in custom_metrics.items():
                if isinstance(pattern, str):
                    pattern = re.compile(pattern, re.IGNORECASE)
                self.PATTERNS[name] = pattern
        
        # Raw metrics storage
        self.raw_metrics = defaultdict(list)
        
        # Aggregated metrics storage
        self.metrics = defaultdict(dict)
        
        # Counter for log entries by level
        self.level_counts = Counter()
        
        # Counter for log entries by logger
        self.logger_counts = Counter()
        
        # Error tracking
        self.errors = {}
        self.error_counts = Counter()
        
        # Threading
        self.lock = threading.RLock()
        self.last_save_time = time.time()
        self.last_aggregation_time = time.time()
        
        # Start background threads
        self._start_background_threads()
    
    def _start_background_threads(self):
        """Start background threads for saving and aggregating metrics."""
        # Start the aggregation thread
        self.aggregation_thread = threading.Thread(
            target=self._aggregation_thread,
            name="MetricsHandler-Aggregation",
            daemon=True
        )
        self.aggregation_thread.start()
        
        # Start the save thread
        self.save_thread = threading.Thread(
            target=self._save_thread,
            name="MetricsHandler-Save",
            daemon=True
        )
        self.save_thread.start()
    
    def emit(self, record):
        """
        Process a log record to extract metrics.
        
        Args:
            record: Log record to process
        """
        try:
            # Update level counts
            self.level_counts[record.levelname] += 1
            
            # Update logger counts
            self.logger_counts[record.name] += 1
            
            # Extract metrics from the log message and record attributes
            self._extract_metrics(record)
            
            # Track errors
            if record.levelno >= logging.ERROR:
                self._track_error(record)
            
            # Check if we need to aggregate or save
            now = time.time()
            if now - self.last_aggregation_time >= self.aggregation_interval:
                self._aggregate_metrics()
                self.last_aggregation_time = now
            
            if now - self.last_save_time >= self.save_interval:
                self._save_metrics()
                self.last_save_time = now
        
        except Exception:
            self.handleError(record)
    
    def _extract_metrics(self, record):
        """
        Extract metrics from a log record.
        
        Args:
            record: Log record to process
        """
        # Get timestamp for this record
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract metrics from the formatted message
        message = self.format(record)
        
        # Extract metrics from patterns
        for metric_name, pattern in self.PATTERNS.items():
            match = pattern.search(message)
            if match:
                try:
                    value = float(match.group(1))
                    # Store in raw metrics
                    with self.lock:
                        self.raw_metrics[metric_name].append((record.created, value))
                except (ValueError, IndexError):
                    pass
        
        # Look for metric_name/metric_value pairs in record attributes
        if hasattr(record, 'metric_name') and hasattr(record, 'metric_value'):
            try:
                metric_name = record.metric_name
                metric_value = float(record.metric_value)
                # Store in raw metrics
                with self.lock:
                    self.raw_metrics[metric_name].append((record.created, metric_value))
            except (ValueError, TypeError):
                pass
        
        # Extract any metrics stored in extra dictionary
        if hasattr(record, 'extra'):
            extra = record.extra
            for key, value in extra.items():
                if key.startswith('metric_') and key != 'metric_name':
                    metric_name = key[7:]  # Remove 'metric_' prefix
                    try:
                        metric_value = float(value)
                        # Store in raw metrics
                        with self.lock:
                            self.raw_metrics[metric_name].append((record.created, metric_value))
                    except (ValueError, TypeError):
                        pass
    
    def _track_error(self, record):
        """
        Track an error log record.
        
        Args:
            record: Error log record
        """
        # Get error info
        if record.exc_info:
            error_type = record.exc_info[0].__name__
            error_message = str(record.exc_info[1])
        else:
            error_type = 'ERROR'
            error_message = record.getMessage()
        
        # Generate an error key for grouping similar errors
        error_key = f"{error_type}:{error_message[:100]}"
        
        # Update error tracking
        with self.lock:
            self.error_counts[error_key] += 1
            
            if error_key not in self.errors:
                self.errors[error_key] = {
                    'type': error_type,
                    'message': error_message,
                    'first_seen': record.created,
                    'last_seen': record.created,
                    'count': 1,
                    'loggers': {record.name: 1}
                }
            else:
                self.errors[error_key]['last_seen'] = record.created
                self.errors[error_key]['count'] += 1
                
                if record.name in self.errors[error_key]['loggers']:
                    self.errors[error_key]['loggers'][record.name] += 1
                else:
                    self.errors[error_key]['loggers'][record.name] = 1
    
    def _aggregate_metrics(self):
        """Aggregate raw metrics for the current time period."""
        now = time.time()
        timestamp = datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
        minute_timestamp = datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:00')
        
        with self.lock:
            # Process each metric type
            for metric_name, values in self.raw_metrics.items():
                if not values:
                    continue
                
                # Filter values for this time period
                period_start = now - self.aggregation_interval
                period_values = [v for t, v in values if t >= period_start]
                
                if not period_values:
                    continue
                
                # Calculate statistics
                count = len(period_values)
                total = sum(period_values)
                minimum = min(period_values)
                maximum = max(period_values)
                average = total / count
                
                # Store aggregated metrics
                self.metrics[minute_timestamp][metric_name] = {
                    'count': count,
                    'total': total,
                    'min': minimum,
                    'max': maximum,
                    'avg': average
                }
                
                # Remove processed values from raw metrics
                self.raw_metrics[metric_name] = [(t, v) for t, v in values if t >= period_start]
            
            # Aggregate log counts
            if self.level_counts:
                self.metrics[minute_timestamp]['log_levels'] = dict(self.level_counts)
                self.level_counts.clear()
            
            if self.logger_counts:
                self.metrics[minute_timestamp]['log_loggers'] = dict(self.logger_counts)
                self.logger_counts.clear()
            
            # Aggregate error counts
            if self.error_counts:
                self.metrics[minute_timestamp]['error_counts'] = dict(self.error_counts)
                self.error_counts.clear()
        
        # Call the metrics callback if provided
        if self.metrics_callback:
            try:
                self.metrics_callback(self.get_current_metrics())
            except Exception as e:
                print(f"Error in metrics callback: {e}")
    
    def _save_metrics(self):
        """Save aggregated metrics to disk."""
        with self.lock:
            if not self.metrics:
                return
            
            # Get today's date for filename
            today = datetime.now().strftime('%Y-%m-%d')
            filename = os.path.join(self.storage_path, f"metrics-{today}.json")
            
            try:
                # Load existing metrics if file exists
                existing_metrics = {}
                if os.path.exists(filename):
                    with open(filename, 'r') as f:
                        existing_metrics = json.load(f)
                
                # Merge with new metrics
                existing_metrics.update(self.metrics)
                
                # Save to file
                with open(filename, 'w') as f:
                    json.dump(existing_metrics, f, indent=2)
                
                # Clear metrics that are more than a day old
                cutoff = time.time() - 86400  # 24 hours
                cutoff_timestamp = datetime.fromtimestamp(cutoff).strftime('%Y-%m-%d %H:%M:00')
                
                self.metrics = {
                    ts: metrics for ts, metrics in self.metrics.items()
                    if ts >= cutoff_timestamp
                }
                
                # Save errors separately
                if self.errors:
                    errors_file = os.path.join(self.storage_path, f"errors-{today}.json")
                    
                    # Convert timestamps to strings for JSON serialization
                    errors_json = {}
                    for key, error in self.errors.items():
                        error_copy = error.copy()
                        error_copy['first_seen'] = datetime.fromtimestamp(error['first_seen']).isoformat()
                        error_copy['last_seen'] = datetime.fromtimestamp(error['last_seen']).isoformat()
                        errors_json[key] = error_copy
                    
                    with open(errors_file, 'w') as f:
                        json.dump(errors_json, f, indent=2)
            
            except Exception as e:
                print(f"Error saving metrics: {e}")
    
    def _aggregation_thread(self):
        """Background thread that periodically aggregates metrics."""
        while True:
            time.sleep(self.aggregation_interval)
            self._aggregate_metrics()
    
    def _save_thread(self):
        """Background thread that periodically saves metrics."""
        while True:
            time.sleep(self.save_interval)
            self._save_metrics()
    
    def get_current_metrics(self):
        """
        Get the current aggregated metrics.
        
        Returns:
            Dictionary with current metrics
        """
        with self.lock:
            return self.metrics.copy()
    
    def get_errors(self):
        """
        Get tracked errors.
        
        Returns:
            Dictionary with error information
        """
        with self.lock:
            return self.errors.copy()
    
    def close(self):
        """Close the handler and save any remaining metrics."""
        self._aggregate_metrics()
        self._save_metrics()
        super().close()