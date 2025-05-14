#!/usr/bin/env python3
"""
Monitoring System Test Script
----------------------------
This script tests the monitoring system by generating metrics, alerts, and simulating
system load. It helps verify that monitoring is working correctly.
"""

import os
import sys
import time
import random
import argparse
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize logging
from utils.logger import setup_logging

# Import monitoring components
try:
    from monitoring.metrics import record_metric
    from monitoring.system_monitor import start_monitoring, stop_monitoring
    from monitoring.performance import track, track_context
    from monitoring.alerting import (
        trigger_alert, AlertSeverity, start_alerting, stop_alerting,
        get_alert_manager, create_standard_rules
    )
    MONITORING_AVAILABLE = True
except ImportError as e:
    print(f"Error importing monitoring components: {e}")
    MONITORING_AVAILABLE = False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Monitoring System Test")
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Duration to run the test in seconds (default: 300)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Interval between metrics in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--spike-interval",
        type=int,
        default=60,
        help="Interval between load spikes in seconds (default: 60)"
    )
    parser.add_argument(
        "--trigger-alerts",
        action="store_true",
        help="Trigger artificial alerts"
    )
    
    return parser.parse_args()


@track(name="cpu_intensive_task")
def cpu_intensive_task(duration=1.0):
    """
    Simulate a CPU-intensive task.
    
    Args:
        duration: Duration of the task in seconds
    """
    start_time = time.time()
    while time.time() - start_time < duration:
        # Generate random numbers
        for _ in range(1000):
            _ = random.random() ** random.random()


@track(name="memory_intensive_task")
def memory_intensive_task(size_mb=100, duration=1.0):
    """
    Simulate a memory-intensive task.
    
    Args:
        size_mb: Size of the memory allocation in MB
        duration: Duration to hold the memory in seconds
    """
    # Allocate memory
    data = [0] * (size_mb * 128 * 1024)  # Roughly size_mb in memory
    
    # Hold for duration
    time.sleep(duration)
    
    # Force data to be used to prevent optimization
    data[0] = 1
    data[-1] = 1
    
    return sum(data)


@track(name="io_intensive_task")
def io_intensive_task(file_size_mb=10, duration=1.0):
    """
    Simulate an I/O-intensive task.
    
    Args:
        file_size_mb: Size of the temp file in MB
        duration: Minimum duration of the task in seconds
    """
    import tempfile
    
    start_time = time.time()
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w+b', delete=True) as f:
        # Write data
        chunk_size = 1024 * 1024  # 1MB
        for _ in range(file_size_mb):
            f.write(os.urandom(chunk_size))
            f.flush()
        
        # Read data
        f.seek(0)
        while f.read(chunk_size):
            pass
        
        # Ensure minimum duration
        elapsed = time.time() - start_time
        if elapsed < duration:
            time.sleep(duration - elapsed)


def trigger_test_alerts():
    """Trigger test alerts of different severities."""
    # Info alert
    trigger_alert(
        name="test_info_alert",
        description="This is a test info alert",
        severity=AlertSeverity.INFO,
        category="test",
        details={"test_id": 1, "timestamp": datetime.now().isoformat()}
    )
    
    # Warning alert
    trigger_alert(
        name="test_warning_alert",
        description="This is a test warning alert",
        severity=AlertSeverity.WARNING,
        category="test",
        details={"test_id": 2, "timestamp": datetime.now().isoformat()}
    )
    
    # Error alert
    trigger_alert(
        name="test_error_alert",
        description="This is a test error alert",
        severity=AlertSeverity.ERROR,
        category="test",
        details={"test_id": 3, "timestamp": datetime.now().isoformat()}
    )
    
    # Critical alert
    trigger_alert(
        name="test_critical_alert",
        description="This is a test critical alert",
        severity=AlertSeverity.CRITICAL,
        category="test",
        details={"test_id": 4, "timestamp": datetime.now().isoformat()}
    )


def create_test_metric_alerts():
    """Create test metric-based alerts."""
    alert_manager = get_alert_manager()
    
    # Add a test CPU alert
    alert_manager.add_metric_rule(
        name="test_high_cpu",
        description="Test high CPU usage",
        metric_name="test.cpu_usage",
        threshold=80,
        operator=">",
        duration=0,
        severity=AlertSeverity.WARNING,
        category="test"
    )
    
    # Add a test memory alert
    alert_manager.add_metric_rule(
        name="test_high_memory",
        description="Test high memory usage",
        metric_name="test.memory_usage",
        threshold=80,
        operator=">",
        duration=0,
        severity=AlertSeverity.WARNING,
        category="test"
    )


def main():
    """Main function."""
    args = parse_args()
    
    # Setup logging
    setup_logging(level="INFO")
    logger = logging.getLogger("monitoring_test")
    
    if not MONITORING_AVAILABLE:
        logger.error("Monitoring components are not available. Cannot run test.")
        return
    
    logger.info("Starting monitoring system test...")
    logger.info(f"Duration: {args.duration} seconds")
    logger.info(f"Interval: {args.interval} seconds")
    logger.info(f"Spike interval: {args.spike_interval} seconds")
    
    try:
        # Start monitoring
        logger.info("Starting system monitoring...")
        start_monitoring()
        
        # Start alerting
        logger.info("Starting alerting system...")
        start_alerting()
        
        # Create standard alert rules
        logger.info("Creating standard alert rules...")
        create_standard_rules()
        
        # Create test metric alerts
        logger.info("Creating test metric alerts...")
        create_test_metric_alerts()
        
        # Record initial metrics
        record_metric("test_start", 1, "test")
        
        # Run the test
        start_time = time.time()
        last_spike_time = 0
        iteration = 0
        
        while time.time() - start_time < args.duration:
            current_time = time.time()
            iteration += 1
            
            # Record basic metrics
            cpu_usage = random.uniform(20, 60)
            memory_usage = random.uniform(30, 70)
            
            record_metric("cpu_usage", cpu_usage, "test")
            record_metric("memory_usage", memory_usage, "test")
            record_metric("iteration", iteration, "test")
            
            # Random metrics
            record_metric("random_value", random.random() * 100, "test")
            import math
            record_metric("sin_wave", 50 + 50 * math.sin(iteration / 10), "test")
            
            # Create a spike in metrics occasionally
            if current_time - last_spike_time > args.spike_interval:
                logger.info("Generating load spike...")
                
                # Spike metrics
                record_metric("cpu_usage", random.uniform(85, 95), "test")
                record_metric("memory_usage", random.uniform(85, 95), "test")
                record_metric("load_spike", 1, "test")
                
                # Generate actual load
                with track_context("load_spike"):
                    # CPU load
                    cpu_intensive_task(duration=random.uniform(1.0, 3.0))
                    
                    # Memory load
                    memory_intensive_task(
                        size_mb=random.randint(100, 500),
                        duration=random.uniform(1.0, 3.0)
                    )
                    
                    # I/O load
                    io_intensive_task(
                        file_size_mb=random.randint(10, 50),
                        duration=random.uniform(1.0, 3.0)
                    )
                
                last_spike_time = current_time
            
            # Trigger test alerts occasionally
            if args.trigger_alerts and random.random() < 0.05:
                logger.info("Triggering test alerts...")
                trigger_test_alerts()
            
            # Sleep until next iteration
            elapsed = time.time() - current_time
            sleep_time = max(0, args.interval - elapsed)
            time.sleep(sleep_time)
        
        # Record final metrics
        record_metric("test_end", 1, "test")
        logger.info("Test completed successfully")
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
    
    finally:
        # Stop monitoring
        logger.info("Stopping monitoring system...")
        stop_monitoring()
        
        # Stop alerting
        logger.info("Stopping alerting system...")
        stop_alerting()
        
        logger.info("Test finished")


if __name__ == "__main__":
    main()