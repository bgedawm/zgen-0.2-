"""
System Monitoring
-------------
This module provides system resource monitoring for the zgen AI Agent.
"""

import os
import time
import threading
import platform
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

# Import platform-specific monitoring libraries
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from monitoring.metrics import record_metric, get_metrics_collector


class SystemMonitor:
    """
    Monitors system resources like CPU, memory, disk, and network.
    """
    
    def __init__(
        self,
        interval=60,  # Collect metrics every 60 seconds
        disk_paths=None,  # Specific disk paths to monitor
        network_interfaces=None,  # Specific network interfaces to monitor
        include_process=True,  # Whether to include process-specific metrics
        auto_start=True  # Whether to start monitoring automatically
    ):
        """
        Initialize the system monitor.
        
        Args:
            interval: Polling interval in seconds
            disk_paths: List of disk paths to monitor (default: all)
            network_interfaces: List of network interfaces to monitor (default: all)
            include_process: Whether to include process-specific metrics
            auto_start: Whether to start monitoring automatically
        """
        self.interval = interval
        self.disk_paths = disk_paths
        self.network_interfaces = network_interfaces
        self.include_process = include_process
        
        # System information
        self.system_info = self._get_system_info()
        
        # Monitoring state
        self.running = False
        self.monitor_thread = None
        
        # Last recorded network counters (for calculating rates)
        self.last_net_io_counters = None
        self.last_net_time = None
        
        # Logger
        self.logger = logging.getLogger('monitoring.system')
        
        # Auto-start if requested
        if auto_start:
            self.start()
    
    def _get_system_info(self):
        """
        Get basic system information.
        
        Returns:
            Dictionary with system information
        """
        info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'hostname': platform.node(),
            'architecture': platform.machine(),
            'processor': platform.processor()
        }
        
        # Add psutil-specific info if available
        if PSUTIL_AVAILABLE:
            try:
                boot_time = datetime.fromtimestamp(psutil.boot_time())
                info['boot_time'] = boot_time.isoformat()
                info['uptime_seconds'] = (datetime.now() - boot_time).total_seconds()
                
                # CPU info
                cpu_info = {}
                cpu_info['physical_cores'] = psutil.cpu_count(logical=False)
                cpu_info['logical_cores'] = psutil.cpu_count(logical=True)
                cpu_info['frequency'] = psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                
                # Memory info
                memory_info = {}
                vm = psutil.virtual_memory()
                memory_info['total'] = vm.total
                memory_info['available'] = vm.available
                
                # Combine
                info['cpu'] = cpu_info
                info['memory'] = memory_info
            except:
                # Ignore any errors
                pass
        
        return info
    
    def start(self):
        """Start the system monitoring thread."""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_thread,
            name="SystemMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info("System monitoring started")
    
    def stop(self):
        """Stop the system monitoring thread."""
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=self.interval + 1)
        self.logger.info("System monitoring stopped")
    
    def _monitor_thread(self):
        """Background thread that periodically collects system metrics."""
        while self.running:
            try:
                self._collect_metrics()
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
            
            # Sleep until next collection
            time.sleep(self.interval)
    
    def _collect_metrics(self):
        """Collect all system metrics."""
        timestamp = time.time()
        
        # Skip if psutil is not available
        if not PSUTIL_AVAILABLE:
            self.logger.warning("psutil is not available, system metrics cannot be collected")
            return
        
        # Collect CPU metrics
        try:
            self._collect_cpu_metrics()
        except Exception as e:
            self.logger.error(f"Error collecting CPU metrics: {e}")
        
        # Collect memory metrics
        try:
            self._collect_memory_metrics()
        except Exception as e:
            self.logger.error(f"Error collecting memory metrics: {e}")
        
        # Collect disk metrics
        try:
            self._collect_disk_metrics()
        except Exception as e:
            self.logger.error(f"Error collecting disk metrics: {e}")
        
        # Collect network metrics
        try:
            self._collect_network_metrics()
        except Exception as e:
            self.logger.error(f"Error collecting network metrics: {e}")
        
        # Collect process metrics if enabled
        if self.include_process:
            try:
                self._collect_process_metrics()
            except Exception as e:
                self.logger.error(f"Error collecting process metrics: {e}")
        
        # Log to system logger
        self.logger.info(
            "System metrics collected",
            extra={
                'event_type': 'system_metrics',
                'timestamp': datetime.fromtimestamp(timestamp).isoformat()
            }
        )
    
    def _collect_cpu_metrics(self):
        """Collect CPU usage metrics."""
        # Overall CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        record_metric('cpu_percent', cpu_percent, 'system')
        
        # Per-CPU usage
        per_cpu_percent = psutil.cpu_percent(interval=None, percpu=True)
        for i, percent in enumerate(per_cpu_percent):
            record_metric(f'cpu{i}_percent', percent, 'system')
        
        # CPU times
        cpu_times = psutil.cpu_times_percent(interval=None)
        record_metric('cpu_user_percent', cpu_times.user, 'system')
        record_metric('cpu_system_percent', cpu_times.system, 'system')
        record_metric('cpu_idle_percent', cpu_times.idle, 'system')
        
        # Load average (Linux/Unix only)
        if hasattr(psutil, 'getloadavg'):
            load1, load5, load15 = psutil.getloadavg()
            record_metric('load_average_1min', load1, 'system')
            record_metric('load_average_5min', load5, 'system')
            record_metric('load_average_15min', load15, 'system')
    
    def _collect_memory_metrics(self):
        """Collect memory usage metrics."""
        # Virtual memory
        vm = psutil.virtual_memory()
        record_metric('memory_total', vm.total, 'system')
        record_metric('memory_available', vm.available, 'system')
        record_metric('memory_used', vm.used, 'system')
        record_metric('memory_percent', vm.percent, 'system')
        
        # Swap memory
        swap = psutil.swap_memory()
        record_metric('swap_total', swap.total, 'system')
        record_metric('swap_used', swap.used, 'system')
        record_metric('swap_percent', swap.percent, 'system')
    
    def _collect_disk_metrics(self):
        """Collect disk usage and I/O metrics."""
        # Disk usage
        if self.disk_paths:
            paths = self.disk_paths
        else:
            # Get all mounted partitions if not specified
            paths = [p.mountpoint for p in psutil.disk_partitions()]
        
        for path in paths:
            try:
                usage = psutil.disk_usage(path)
                safe_path = path.replace('/', '_').replace('\\', '_').strip('_')
                record_metric(f'disk_{safe_path}_total', usage.total, 'system')
                record_metric(f'disk_{safe_path}_used', usage.used, 'system')
                record_metric(f'disk_{safe_path}_percent', usage.percent, 'system')
            except (FileNotFoundError, PermissionError):
                # Skip if the path is not accessible
                pass
        
        # Disk I/O
        io_counters = psutil.disk_io_counters()
        record_metric('disk_read_count', io_counters.read_count, 'system')
        record_metric('disk_write_count', io_counters.write_count, 'system')
        record_metric('disk_read_bytes', io_counters.read_bytes, 'system')
        record_metric('disk_write_bytes', io_counters.write_bytes, 'system')
    
    def _collect_network_metrics(self):
        """Collect network usage metrics."""
        # Get network I/O counters
        if self.network_interfaces:
            # Get specific interfaces if requested
            net_io = psutil.net_io_counters(pernic=True)
            net_io_counters = {}
            for nic in self.network_interfaces:
                if nic in net_io:
                    net_io_counters[nic] = net_io[nic]
        else:
            # Get overall counters
            net_io_counters = {'total': psutil.net_io_counters(pernic=False)}
        
        # Current time
        current_time = time.time()
        
        # Calculate rates if we have previous measurements
        if self.last_net_io_counters and self.last_net_time:
            time_diff = current_time - self.last_net_time
            
            for nic, counters in net_io_counters.items():
                if nic in self.last_net_io_counters:
                    last_counters = self.last_net_io_counters[nic]
                    
                    # Calculate bytes per second
                    bytes_sent_per_sec = (counters.bytes_sent - last_counters.bytes_sent) / time_diff
                    bytes_recv_per_sec = (counters.bytes_recv - last_counters.bytes_recv) / time_diff
                    
                    # Record rates
                    prefix = 'network_total_' if nic == 'total' else f'network_{nic}_'
                    record_metric(f'{prefix}bytes_sent_per_sec', bytes_sent_per_sec, 'system')
                    record_metric(f'{prefix}bytes_recv_per_sec', bytes_recv_per_sec, 'system')
        
        # Record totals
        for nic, counters in net_io_counters.items():
            prefix = 'network_total_' if nic == 'total' else f'network_{nic}_'
            record_metric(f'{prefix}bytes_sent', counters.bytes_sent, 'system')
            record_metric(f'{prefix}bytes_recv', counters.bytes_recv, 'system')
            record_metric(f'{prefix}packets_sent', counters.packets_sent, 'system')
            record_metric(f'{prefix}packets_recv', counters.packets_recv, 'system')
        
        # Save current counters for next time
        self.last_net_io_counters = net_io_counters
        self.last_net_time = current_time
    
    def _collect_process_metrics(self):
        """Collect metrics for the current process."""
        try:
            # Get the current process
            process = psutil.Process()
            
            # CPU usage
            try:
                cpu_percent = process.cpu_percent(interval=None)
                record_metric('process_cpu_percent', cpu_percent, 'system')
            except:
                pass
            
            # Memory usage
            try:
                memory_info = process.memory_info()
                record_metric('process_memory_rss', memory_info.rss, 'system')
                record_metric('process_memory_vms', memory_info.vms, 'system')
            except:
                pass
            
            # Open files
            try:
                open_files = process.open_files()
                record_metric('process_open_files', len(open_files), 'system')
            except:
                pass
            
            # Threads
            try:
                threads = process.threads()
                record_metric('process_threads', len(threads), 'system')
            except:
                pass
            
            # Connections
            try:
                connections = process.connections()
                record_metric('process_connections', len(connections), 'system')
            except:
                pass
            
            # Child processes
            try:
                children = process.children(recursive=True)
                record_metric('process_children', len(children), 'system')
            except:
                pass
            
            # Process age
            try:
                create_time = process.create_time()
                age = time.time() - create_time
                record_metric('process_age_seconds', age, 'system')
            except:
                pass
        
        except Exception as e:
            self.logger.error(f"Error collecting process metrics: {e}")
    
    def get_system_info(self):
        """
        Get basic system information.
        
        Returns:
            Dictionary with system information
        """
        return self.system_info.copy()


# Singleton instance
_system_monitor = None

def get_system_monitor():
    """
    Get the singleton system monitor instance.
    
    Returns:
        SystemMonitor instance
    """
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


def start_monitoring():
    """Start system monitoring."""
    monitor = get_system_monitor()
    monitor.start()


def stop_monitoring():
    """Stop system monitoring."""
    monitor = get_system_monitor()
    monitor.stop()


def get_system_info():
    """
    Get basic system information.
    
    Returns:
        Dictionary with system information
    """
    monitor = get_system_monitor()
    return monitor.get_system_info()