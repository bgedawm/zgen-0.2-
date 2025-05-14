# Monitoring and Logging System

The zgen AI Agent includes a comprehensive monitoring and logging system that helps track the performance, health, and activities of the agent. This document explains how to use and extend this system.

## Overview

The monitoring and logging system consists of several components:

1. **Logging System**: Captures structured log messages at different levels and from different components
2. **Metrics Collection**: Tracks numerical metrics over time for quantitative analysis
3. **System Monitoring**: Monitors system resources like CPU, memory, disk, and network
4. **Performance Tracking**: Measures execution time and success rates of various operations
5. **Alerting System**: Notifies about critical issues or important events
6. **Dashboards**: Visualizes monitoring data for easy analysis

## Accessing the Monitoring Dashboard

The monitoring dashboard is available at:

```
http://localhost:8001/monitoring
```

This dashboard provides a user-friendly interface for viewing system metrics, performance data, alerts, and logs.

## Available Dashboards

The monitoring system includes several dashboards:

1. **System Dashboard**: Displays system resource usage (CPU, memory, disk, network)
2. **Performance Dashboard**: Shows execution times and call counts for various operations
3. **Alerts Dashboard**: Lists active alerts and alert history
4. **Logs Dashboard**: Displays and filters log messages

## Monitoring API Endpoints

The monitoring system exposes the following API endpoints:

### General Monitoring

- `GET /api/monitoring`: Get overall monitoring status
- `GET /api/monitoring/metrics`: Get all collected metrics
- `GET /api/monitoring/metrics/{metric_name}`: Get history for a specific metric
- `POST /api/monitoring/metrics`: Record a custom metric

### Alerts

- `GET /api/monitoring/alerts`: Get all active alerts
- `GET /api/monitoring/alerts/history`: Get alert history
- `POST /api/monitoring/alerts`: Create and trigger a new alert
- `PUT /api/monitoring/alerts/{name}/acknowledge`: Acknowledge an alert
- `PUT /api/monitoring/alerts/{name}/resolve`: Resolve an alert
- `PUT /api/monitoring/alerts/{name}/silence`: Silence or unsilence an alert

### Dashboards

- `GET /api/monitoring/dashboard`: Get the dashboard index page
- `GET /api/monitoring/dashboard/{name}`: Get a specific dashboard (html or json format)

### Performance

- `GET /api/monitoring/performance`: Get performance statistics

### Control

- `POST /api/monitoring/control/start`: Start the monitoring and alerting system
- `POST /api/monitoring/control/stop`: Stop the monitoring and alerting system

## Logging

### Log Levels

The logging system supports the following log levels, in order of increasing severity:

1. `DEBUG`: Detailed information, typically of interest only for diagnosing problems
2. `INFO`: Confirmation that things are working as expected
3. `WARNING`: An indication that something unexpected happened, or a potential problem in the near future
4. `ERROR`: A more serious problem that prevented some functionality from working correctly
5. `CRITICAL`: A very serious error, indicating that the program itself may be unable to continue running

### Log Components

Logs are categorized by component, making it easier to filter and analyze specific parts of the system:

- `agent`: Core agent functionality
- `api`: API server
- `scheduler`: Task scheduling system
- `monitoring`: Monitoring and alerting system
- `task`: Task execution

### Structured Logging

The logging system captures structured data with each log message, including:

- Timestamp
- Log level
- Component
- Message
- Additional context data

### Log Storage

Logs are stored in the following locations:

- Main logs: `data/logs/zgen.log` (and rotated files)
- Error logs: `data/logs/errors/error.log` (and rotated files)
- Task logs: `data/logs/tasks/{task_id}.log`

## Metrics

### Metric Categories

Metrics are grouped into categories:

- `system`: System resource metrics (CPU, memory, disk, network)
- `agent`: Agent-specific metrics
- `api`: API request/response metrics
- `tasks`: Task execution metrics
- `performance`: Performance metrics for various operations
- `logs`: Log-related metrics

### Custom Metrics

You can record custom metrics using the API:

```
POST /api/monitoring/metrics
{
  "name": "my_custom_metric",
  "value": 42.5,
  "category": "custom"
}
```

### Metric Storage

Metrics are stored in the following locations:

- Metrics data: `data/metrics/` directory

## Alerts

### Alert Severity Levels

The alerting system supports multiple severity levels:

1. `INFO`: Informational alerts that don't require immediate action
2. `WARNING`: Potential issues that might require attention
3. `ERROR`: Serious issues that require attention
4. `CRITICAL`: Critical issues that require immediate attention

### Creating Alerts

You can create and trigger alerts using the API:

```
POST /api/monitoring/alerts
{
  "name": "high_memory_usage",
  "description": "Memory usage is above 90%",
  "severity": "warning",
  "category": "system"
}
```

### Alert Rules

The system supports alert rules that automatically trigger alerts based on conditions:

- Metric-based rules: Trigger alerts when metrics exceed thresholds
- Complex rules: Custom rules based on multiple conditions

## Extending the Monitoring System

### Adding Custom Metrics

From Python code, you can add custom metrics:

```python
from monitoring.metrics import record_metric

# Record a metric value
record_metric("my_custom_metric", 42.5, "custom")
```

### Performance Tracking

You can track the performance of functions:

```python
from monitoring.performance import track, track_context

# Track a function execution time
@track()
def my_function():
    # Function body
    pass

# Track a code block execution time
with track_context("my_operation"):
    # Code block
    pass
```

### Creating Alert Rules

You can create custom alert rules:

```python
from monitoring.alerting import get_alert_manager, AlertSeverity

# Get the alert manager
alert_manager = get_alert_manager()

# Add a metric-based alert rule
alert_manager.add_metric_rule(
    name="high_cpu_usage",
    description="High CPU usage detected",
    metric_name="system.cpu_percent",
    threshold=90,
    operator=">",
    duration=300,  # 5 minutes
    severity=AlertSeverity.WARNING,
    category="system"
)
```

## Configuration

The monitoring and logging system can be configured through the following files:

- `logging/logging.yaml`: Logging configuration
- Environment variables in `.env` file:
  - `LOG_LEVEL`: Default log level
  - `LOG_TO_FILE`: Whether to log to file
  - `LOG_TO_CONSOLE`: Whether to log to console
  - `MONITORING_ENABLED`: Whether to enable monitoring
  - `ALERTING_ENABLED`: Whether to enable alerting

## Troubleshooting

### Common Issues

1. **High disk usage**: Check log rotation settings if logs are taking too much space
2. **Performance impact**: Reduce logging level to INFO or WARNING if the system is being slowed down
3. **Missing metrics**: Ensure the monitoring system is enabled and properly initialized

### Resetting the Monitoring System

If you need to reset the monitoring system:

1. Stop the application
2. Delete the `data/metrics` directory
3. Restart the application

## Best Practices

1. Use appropriate log levels to maintain a clean log file
2. Create alerts for important conditions that need attention
3. Regularly review the monitoring dashboard for performance trends
4. Configure log rotation to prevent excessive disk usage
5. Add metrics for key application KPIs to track over time