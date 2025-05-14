"""
Monitoring System
-------------
This package provides monitoring and alerting for the zgen AI Agent.
"""

from monitoring.metrics import (
    get_metrics_collector, record_metric, get_metric_history,
    get_metric_average, get_all_metrics, register_callback
)

from monitoring.system_monitor import (
    get_system_monitor, start_monitoring, stop_monitoring,
    get_system_info
)

from monitoring.performance import (
    track, track_async, track_context, get_tracker, report_stats
)

from monitoring.alerting import (
    get_alert_manager, start_alerting, stop_alerting, trigger_alert,
    AlertSeverity, AlertStatus, Alert, AlertRule, MetricAlertRule,
    create_standard_rules
)

from monitoring.dashboards.dashboard import (
    get_dashboard_manager, get_dashboard, render_dashboard,
    render_dashboard_index, Dashboard, SystemDashboard,
    PerformanceDashboard, AlertDashboard
)

__all__ = [
    # Metrics
    'get_metrics_collector', 'record_metric', 'get_metric_history',
    'get_metric_average', 'get_all_metrics', 'register_callback',
    
    # System monitoring
    'get_system_monitor', 'start_monitoring', 'stop_monitoring',
    'get_system_info',
    
    # Performance tracking
    'track', 'track_async', 'track_context', 'get_tracker', 'report_stats',
    
    # Alerting
    'get_alert_manager', 'start_alerting', 'stop_alerting', 'trigger_alert',
    'AlertSeverity', 'AlertStatus', 'Alert', 'AlertRule', 'MetricAlertRule',
    'create_standard_rules',
    
    # Dashboards
    'get_dashboard_manager', 'get_dashboard', 'render_dashboard',
    'render_dashboard_index', 'Dashboard', 'SystemDashboard',
    'PerformanceDashboard', 'AlertDashboard'
]


def initialize_monitoring():
    """Initialize the monitoring system."""
    # Start system monitoring
    start_monitoring()
    
    # Start alerting
    start_alerting()
    
    # Create standard alert rules
    create_standard_rules()
    
    # Initialize dashboard manager
    get_dashboard_manager()


def shutdown_monitoring():
    """Shut down the monitoring system."""
    # Stop monitoring
    stop_monitoring()
    
    # Stop alerting
    stop_alerting()