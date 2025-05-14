"""
Tests for the monitoring system
"""

import os
import time
import unittest
import tempfile
from unittest.mock import patch, MagicMock

# Import the modules to test
from monitoring.metrics import (
    record_metric,
    get_metric_history,
    get_metric_average,
    get_all_metrics,
    MetricsCollector
)
from monitoring.system_monitor import (
    SystemMonitor,
    start_monitoring,
    stop_monitoring
)
from monitoring.performance import (
    track,
    track_async,
    track_context,
    PerformanceTracker
)
from monitoring.alerting import (
    AlertSeverity,
    AlertStatus,
    Alert,
    AlertRule,
    MetricAlertRule,
    AlertManager,
    trigger_alert,
    get_alert_manager
)


class TestMetrics(unittest.TestCase):
    """Test the metrics collection system."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for metrics storage
        self.temp_dir = tempfile.mkdtemp()
        self.collector = MetricsCollector(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_record_metric(self):
        """Test recording a metric."""
        # Record a metric
        self.collector.record_metric("test_metric", 42.0, "test")
        
        # Get the metric history
        history = self.collector.get_metric_history("test.test_metric")
        
        # Check that the metric was recorded
        self.assertGreater(len(history), 0)
        self.assertEqual(history[-1][1], 42.0)
    
    def test_get_metric_average(self):
        """Test getting the average of a metric."""
        # Record multiple values
        self.collector.record_metric("avg_metric", 10.0, "test")
        self.collector.record_metric("avg_metric", 20.0, "test")
        self.collector.record_metric("avg_metric", 30.0, "test")
        
        # Get the average
        avg = self.collector.get_metric_average("test.avg_metric")
        
        # Check the average
        self.assertEqual(avg, 20.0)
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        # Record metrics in different categories
        self.collector.record_metric("metric1", 1.0, "category1")
        self.collector.record_metric("metric2", 2.0, "category2")
        
        # Get all metrics
        metrics = self.collector.get_all_metrics()
        
        # Check that both metrics are in the result
        self.assertIn("category1.metric1", metrics)
        self.assertIn("category2.metric2", metrics)


class TestPerformance(unittest.TestCase):
    """Test the performance tracking system."""
    
    def setUp(self):
        """Set up the test environment."""
        self.tracker = PerformanceTracker(category="test")
    
    def test_track_decorator(self):
        """Test the track decorator."""
        # Create a tracked function
        @self.tracker.track()
        def test_function():
            time.sleep(0.1)
            return 42
        
        # Call the function
        result = test_function()
        
        # Check the result
        self.assertEqual(result, 42)
        
        # Check that metrics were recorded
        # Note: This would require setting up a mock for record_metric
        # which is beyond the scope of this simple test
    
    def test_track_context(self):
        """Test the track_context context manager."""
        # Use the context manager
        with self.tracker.track_context("test_context"):
            time.sleep(0.1)
        
        # Again, we would need to mock record_metric to verify
        # that metrics were recorded


class TestAlerts(unittest.TestCase):
    """Test the alerting system."""
    
    def setUp(self):
        """Set up the test environment."""
        self.alert = Alert(
            name="test_alert",
            description="Test alert",
            severity=AlertSeverity.WARNING,
            category="test"
        )
    
    def test_alert_trigger(self):
        """Test triggering an alert."""
        # Trigger the alert
        result = self.alert.trigger({"test_detail": "value"})
        
        # Check that the alert was triggered
        self.assertTrue(result)
        self.assertEqual(self.alert.status, AlertStatus.ACTIVE)
        self.assertIsNotNone(self.alert.triggered_at)
        self.assertEqual(self.alert.details, {"test_detail": "value"})
    
    def test_alert_acknowledge(self):
        """Test acknowledging an alert."""
        # Trigger the alert
        self.alert.trigger()
        
        # Acknowledge the alert
        result = self.alert.acknowledge("test_user")
        
        # Check that the alert was acknowledged
        self.assertTrue(result)
        self.assertEqual(self.alert.status, AlertStatus.ACKNOWLEDGED)
        self.assertEqual(self.alert.acknowledged_by, "test_user")
    
    def test_alert_resolve(self):
        """Test resolving an alert."""
        # Trigger the alert
        self.alert.trigger()
        
        # Resolve the alert
        result = self.alert.resolve()
        
        # Check that the alert was resolved
        self.assertTrue(result)
        self.assertEqual(self.alert.status, AlertStatus.RESOLVED)
    
    def test_alert_rule(self):
        """Test an alert rule."""
        # Create a condition that always returns True
        condition = lambda: True
        
        # Create an alert rule
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            condition=condition,
            alert=self.alert
        )
        
        # Check the rule
        result = rule.check()
        
        # Check that the alert was triggered
        self.assertTrue(result)
        self.assertEqual(self.alert.status, AlertStatus.ACTIVE)


class TestSystemMonitor(unittest.TestCase):
    """Test the system monitoring."""
    
    @patch('psutil.cpu_percent')
    def test_system_monitor(self, mock_cpu_percent):
        """Test basic system monitoring."""
        # Mock the psutil function to return a fixed value
        mock_cpu_percent.return_value = 50.0
        
        # Create a monitor with a very short interval
        monitor = SystemMonitor(interval=0.1, auto_start=False)
        
        # Check that system info was collected
        self.assertIsNotNone(monitor.system_info)
        self.assertIn('platform', monitor.system_info)


if __name__ == '__main__':
    unittest.main()