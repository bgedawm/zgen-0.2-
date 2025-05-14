# Monitoring and Alerting System

This directory contains the monitoring and alerting system for the zgen AI Agent. The system provides comprehensive monitoring of system resources, performance metrics, and application health, along with alerting and visualization capabilities.

## Components

### 1. Metrics Collection

The `metrics.py` module provides functionality for collecting, storing, and retrieving metrics:

- Record custom metrics with timestamps
- Track metric history
- Calculate metric averages over time windows
- Register callbacks for metric updates

### 2. System Monitoring

The `system_monitor.py` module monitors system resources:

- CPU usage (overall and per-core)
- Memory usage (RAM and swap)
- Disk usage and I/O
- Network traffic
- Process-specific metrics

### 3. Performance Monitoring

The `performance.py` module provides tools for tracking execution performance:

- Function execution time tracking
- Success/failure tracking
- Async function tracking
- Code block tracking with context managers

### 4. Alerting System

The `alerting.py` module provides a flexible alerting system:

- Define alerts with different severity levels
- Create alert rules based on metrics or custom conditions
- Track alert history
- Send notifications through various channels
- Manage alert lifecycle (acknowledgment, resolution)

### 5. Dashboards

The `dashboards` directory contains visualization components:

- System dashboard
- Performance dashboard
- Alerts dashboard
- Custom dashboards

## Usage

### Recording Metrics

```python
from monitoring.metrics import record_metric

# Record a metric
record_metric("cpu_usage", 45.2, "system")

# Get metric history
from monitoring.metrics import get_metric_history
history = get_metric_history("system.cpu_usage")

# Get metric average
from monitoring.metrics import get_metric_average
avg = get_metric_average("system.cpu_usage", window_seconds=300)
```

### Tracking Performance

```python
from monitoring.performance import track, track_async, track_context

# Track function execution time
@track()
def my_function():
    # Function code
    pass

# Track async function
@track_async()
async def my_async_function():
    # Async function code
    pass

# Track code block
with track_context("my_operation"):
    # Code block
    pass
```

### Creating Alerts

```python
from monitoring.alerting import trigger_alert, AlertSeverity

# Trigger an alert
trigger_alert(
    name="high_memory_usage",
    description="Memory usage is above 90%",
    severity=AlertSeverity.WARNING,
    category="system",
    details={"memory_percent": 92.5}
)

# Create an alert rule based on a metric
from monitoring.alerting import get_alert_manager
alert_manager = get_alert_manager()

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

### Working with Dashboards

```python
from monitoring.dashboards.dashboard import render_dashboard

# Render a dashboard
html = render_dashboard("system", format="html")
json_data = render_dashboard("system", format="json")

# Get the dashboard index
from monitoring.dashboards.dashboard import render_dashboard_index
index_html = render_dashboard_index()
```

## Configuration

The monitoring system can be configured through the following environment variables:

- `MONITORING_ENABLED`: Whether to enable monitoring (default: `true`)
- `MONITORING_INTERVAL`: Interval for system metrics collection in seconds (default: `60`)
- `METRICS_RETENTION_DAYS`: Number of days to retain metrics (default: `30`)
- `ALERTING_ENABLED`: Whether to enable alerting (default: `true`)
- `ALERTING_NOTIFICATIONS`: Whether to send alert notifications (default: `true`)

## API Endpoints

The monitoring system exposes the following API endpoints:

- `/api/monitoring`: Get monitoring status
- `/api/monitoring/metrics`: Get all metrics
- `/api/monitoring/metrics/{metric_name}`: Get specific metric history
- `/api/monitoring/alerts`: Get active alerts
- `/api/monitoring/alerts/history`: Get alert history
- `/api/monitoring/dashboard`: Get dashboard index
- `/api/monitoring/dashboard/{name}`: Get specific dashboard
- `/api/monitoring/performance`: Get performance statistics

## Integration with Other Components

The monitoring system integrates with other components of the zgen AI Agent:

- **Core Agent**: Tracks performance of agent operations
- **API Server**: Monitors API requests and responses
- **Task Scheduler**: Tracks scheduled task execution
- **LLM Integration**: Monitors token usage and latency

## Web Interface

The monitoring system includes a web interface that can be accessed at:

```
http://localhost:8001/monitoring
```

This interface provides visualizations of all monitoring data and allows for managing alerts and viewing logs.

## Extending the System

To add custom metrics to the monitoring system:

1. Import the `record_metric` function from `monitoring.metrics`
2. Call it with your metric name, value, and optional category
3. Use the API to query your metrics or create alerts based on them

To add custom dashboards:

1. Create a new class that inherits from `Dashboard` in `dashboards/dashboard.py`
2. Implement the `get_data()` and `to_html()` methods
3. Register your dashboard with the dashboard manager