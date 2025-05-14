"""
Monitoring Dashboards
----------------
This module provides visualization dashboards for the zgen AI Agent metrics.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from monitoring.metrics import get_all_metrics, get_metric_history
from monitoring.alerting import get_alert_manager, AlertStatus


class Dashboard:
    """
    Base class for monitoring dashboards.
    """
    
    def __init__(self, name: str):
        """
        Initialize a dashboard.
        
        Args:
            name: Dashboard name
        """
        self.name = name
        self.logger = logging.getLogger('monitoring.dashboard')
    
    def get_data(self) -> Dict[str, Any]:
        """
        Get dashboard data.
        
        Returns:
            Dashboard data
        """
        raise NotImplementedError("Subclasses must implement get_data")
    
    def to_html(self) -> str:
        """
        Convert dashboard data to HTML.
        
        Returns:
            HTML representation of the dashboard
        """
        raise NotImplementedError("Subclasses must implement to_html")
    
    def to_json(self) -> str:
        """
        Convert dashboard data to JSON.
        
        Returns:
            JSON representation of the dashboard
        """
        return json.dumps(self.get_data())


class SystemDashboard(Dashboard):
    """
    Dashboard for system metrics.
    """
    
    def __init__(self):
        """Initialize the system dashboard."""
        super().__init__("System")
    
    def get_data(self) -> Dict[str, Any]:
        """
        Get system dashboard data.
        
        Returns:
            System dashboard data
        """
        # Get system metrics
        system_metrics = {}
        
        # Get all metrics
        all_metrics = get_all_metrics()
        
        # Filter system metrics
        for metric_name, values in all_metrics.items():
            if metric_name.startswith('system.'):
                system_metrics[metric_name] = values
        
        # Get latest values
        latest_values = {}
        for metric_name, values in system_metrics.items():
            if values:
                # Get the most recent value
                latest_values[metric_name] = values[-1][1]
        
        # Group metrics by type
        grouped_metrics = {
            'cpu': {},
            'memory': {},
            'disk': {},
            'network': {},
            'process': {},
            'other': {}
        }
        
        for metric_name, value in latest_values.items():
            if 'cpu' in metric_name:
                grouped_metrics['cpu'][metric_name] = value
            elif 'memory' in metric_name:
                grouped_metrics['memory'][metric_name] = value
            elif 'disk' in metric_name:
                grouped_metrics['disk'][metric_name] = value
            elif 'network' in metric_name:
                grouped_metrics['network'][metric_name] = value
            elif 'process' in metric_name:
                grouped_metrics['process'][metric_name] = value
            else:
                grouped_metrics['other'][metric_name] = value
        
        # Get time series data for charts
        charts = {}
        
        # CPU chart
        cpu_metrics = get_metric_history('system.cpu_percent', 60)
        charts['cpu'] = {
            'labels': [item[0] for item in cpu_metrics],
            'values': [item[1] for item in cpu_metrics]
        }
        
        # Memory chart
        memory_metrics = get_metric_history('system.memory_percent', 60)
        charts['memory'] = {
            'labels': [item[0] for item in memory_metrics],
            'values': [item[1] for item in memory_metrics]
        }
        
        # Disk I/O chart
        disk_read_metrics = get_metric_history('system.disk_read_bytes', 60)
        disk_write_metrics = get_metric_history('system.disk_write_bytes', 60)
        
        if disk_read_metrics and disk_write_metrics:
            charts['disk_io'] = {
                'labels': [item[0] for item in disk_read_metrics],
                'read_values': [item[1] for item in disk_read_metrics],
                'write_values': [item[1] for item in disk_write_metrics]
            }
        
        # Network I/O chart
        net_recv_metrics = get_metric_history('system.network_total_bytes_recv_per_sec', 60)
        net_sent_metrics = get_metric_history('system.network_total_bytes_sent_per_sec', 60)
        
        if net_recv_metrics and net_sent_metrics:
            charts['network_io'] = {
                'labels': [item[0] for item in net_recv_metrics],
                'recv_values': [item[1] for item in net_recv_metrics],
                'sent_values': [item[1] for item in net_sent_metrics]
            }
        
        return {
            'name': self.name,
            'timestamp': datetime.now().isoformat(),
            'metrics': grouped_metrics,
            'charts': charts
        }
    
    def to_html(self) -> str:
        """
        Convert system dashboard data to HTML.
        
        Returns:
            HTML representation of the system dashboard
        """
        data = self.get_data()
        
        html = f"""
        <div class="dashboard system-dashboard">
            <h2>System Dashboard</h2>
            <p>Last updated: {data['timestamp']}</p>
            
            <div class="dashboard-row">
                <div class="dashboard-cell">
                    <h3>CPU Usage</h3>
                    <div class="metric-chart" id="cpu-chart"></div>
                    <div class="metric-values">
        """
        
        # Add CPU metrics
        for metric_name, value in data['metrics']['cpu'].items():
            display_name = metric_name.replace('system.', '').replace('_', ' ').title()
            html += f"<div><span>{display_name}:</span> <span>{value:.2f}%</span></div>"
        
        html += """
                    </div>
                </div>
                
                <div class="dashboard-cell">
                    <h3>Memory Usage</h3>
                    <div class="metric-chart" id="memory-chart"></div>
                    <div class="metric-values">
        """
        
        # Add memory metrics
        for metric_name, value in data['metrics']['memory'].items():
            if 'percent' in metric_name:
                display_name = metric_name.replace('system.', '').replace('_', ' ').title()
                html += f"<div><span>{display_name}:</span> <span>{value:.2f}%</span></div>"
            else:
                display_name = metric_name.replace('system.', '').replace('_', ' ').title()
                # Convert bytes to MB or GB
                if value > 1073741824:  # 1 GB
                    html += f"<div><span>{display_name}:</span> <span>{value/1073741824:.2f} GB</span></div>"
                else:
                    html += f"<div><span>{display_name}:</span> <span>{value/1048576:.2f} MB</span></div>"
        
        html += """
                    </div>
                </div>
            </div>
            
            <div class="dashboard-row">
                <div class="dashboard-cell">
                    <h3>Disk Usage</h3>
                    <div class="metric-values">
        """
        
        # Add disk metrics
        for metric_name, value in data['metrics']['disk'].items():
            if 'percent' in metric_name:
                display_name = metric_name.replace('system.', '').replace('_', ' ').title()
                html += f"<div><span>{display_name}:</span> <span>{value:.2f}%</span></div>"
            elif 'total' in metric_name or 'used' in metric_name:
                display_name = metric_name.replace('system.', '').replace('_', ' ').title()
                # Convert bytes to MB or GB
                if value > 1073741824:  # 1 GB
                    html += f"<div><span>{display_name}:</span> <span>{value/1073741824:.2f} GB</span></div>"
                else:
                    html += f"<div><span>{display_name}:</span> <span>{value/1048576:.2f} MB</span></div>"
        
        html += """
                    </div>
                    <div class="metric-chart" id="disk-io-chart"></div>
                </div>
                
                <div class="dashboard-cell">
                    <h3>Network Usage</h3>
                    <div class="metric-chart" id="network-io-chart"></div>
                    <div class="metric-values">
        """
        
        # Add network metrics
        for metric_name, value in data['metrics']['network'].items():
            if 'per_sec' in metric_name:
                display_name = metric_name.replace('system.', '').replace('_', ' ').title()
                # Convert bytes to KB or MB per second
                if value > 1048576:  # 1 MB
                    html += f"<div><span>{display_name}:</span> <span>{value/1048576:.2f} MB/s</span></div>"
                else:
                    html += f"<div><span>{display_name}:</span> <span>{value/1024:.2f} KB/s</span></div>"
        
        html += """
                    </div>
                </div>
            </div>
            
            <div class="dashboard-row">
                <div class="dashboard-cell">
                    <h3>Process Stats</h3>
                    <div class="metric-values">
        """
        
        # Add process metrics
        for metric_name, value in data['metrics']['process'].items():
            display_name = metric_name.replace('system.', '').replace('_', ' ').title()
            
            # Format value based on type
            if 'memory' in metric_name:
                # Convert bytes to MB or GB
                if value > 1073741824:  # 1 GB
                    formatted_value = f"{value/1073741824:.2f} GB"
                else:
                    formatted_value = f"{value/1048576:.2f} MB"
            elif 'percent' in metric_name:
                formatted_value = f"{value:.2f}%"
            elif 'age' in metric_name and 'seconds' in metric_name:
                # Convert seconds to hours:minutes:seconds
                hours, remainder = divmod(int(value), 3600)
                minutes, seconds = divmod(remainder, 60)
                formatted_value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                formatted_value = str(value)
            
            html += f"<div><span>{display_name}:</span> <span>{formatted_value}</span></div>"
        
        html += """
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // CPU chart
            var cpuChart = new Chart(document.getElementById('cpu-chart').getContext('2d'), {
                type: 'line',
                data: {
                    labels: CHART_DATA.cpu.labels,
                    datasets: [{
                        label: 'CPU Usage',
                        data: CHART_DATA.cpu.values,
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderWidth: 2,
                        fill: true
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: 'Usage (%)'
                            }
                        }
                    },
                    animation: false,
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
            
            // Memory chart
            var memoryChart = new Chart(document.getElementById('memory-chart').getContext('2d'), {
                type: 'line',
                data: {
                    labels: CHART_DATA.memory.labels,
                    datasets: [{
                        label: 'Memory Usage',
                        data: CHART_DATA.memory.values,
                        borderColor: 'rgba(153, 102, 255, 1)',
                        backgroundColor: 'rgba(153, 102, 255, 0.2)',
                        borderWidth: 2,
                        fill: true
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: 'Usage (%)'
                            }
                        }
                    },
                    animation: false,
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        </script>
        """
        
        # Add disk I/O chart if data is available
        if 'disk_io' in data['charts']:
            html += """
            <script>
                // Disk I/O chart
                var diskIOChart = new Chart(document.getElementById('disk-io-chart').getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: CHART_DATA.disk_io.labels,
                        datasets: [{
                            label: 'Read',
                            data: CHART_DATA.disk_io.read_values,
                            borderColor: 'rgba(54, 162, 235, 1)',
                            backgroundColor: 'rgba(54, 162, 235, 0.2)',
                            borderWidth: 2,
                            fill: false
                        },
                        {
                            label: 'Write',
                            data: CHART_DATA.disk_io.write_values,
                            borderColor: 'rgba(255, 99, 132, 1)',
                            backgroundColor: 'rgba(255, 99, 132, 0.2)',
                            borderWidth: 2,
                            fill: false
                        }]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Bytes'
                                }
                            }
                        },
                        animation: false,
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });
            </script>
            """
        
        # Add network I/O chart if data is available
        if 'network_io' in data['charts']:
            html += """
            <script>
                // Network I/O chart
                var networkIOChart = new Chart(document.getElementById('network-io-chart').getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: CHART_DATA.network_io.labels,
                        datasets: [{
                            label: 'Received',
                            data: CHART_DATA.network_io.recv_values,
                            borderColor: 'rgba(54, 162, 235, 1)',
                            backgroundColor: 'rgba(54, 162, 235, 0.2)',
                            borderWidth: 2,
                            fill: false
                        },
                        {
                            label: 'Sent',
                            data: CHART_DATA.network_io.sent_values,
                            borderColor: 'rgba(255, 99, 132, 1)',
                            backgroundColor: 'rgba(255, 99, 132, 0.2)',
                            borderWidth: 2,
                            fill: false
                        }]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Bytes/s'
                                }
                            }
                        },
                        animation: false,
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });
            </script>
            """
        
        # Replace chart data placeholder with actual data
        html = html.replace('CHART_DATA', json.dumps(data['charts']))
        
        return html


class PerformanceDashboard(Dashboard):
    """
    Dashboard for performance metrics.
    """
    
    def __init__(self):
        """Initialize the performance dashboard."""
        super().__init__("Performance")
    
    def get_data(self) -> Dict[str, Any]:
        """
        Get performance dashboard data.
        
        Returns:
            Performance dashboard data
        """
        # Get performance metrics
        performance_metrics = {}
        
        # Get all metrics
        all_metrics = get_all_metrics()
        
        # Filter performance metrics
        for metric_name, values in all_metrics.items():
            if metric_name.startswith('performance.') or '_duration' in metric_name:
                performance_metrics[metric_name] = values
        
        # Calculate average, min, max for each metric
        stats = {}
        for metric_name, values in performance_metrics.items():
            if not values:
                continue
            
            # Get only the values (not timestamps)
            metric_values = [value for _, value in values]
            
            stats[metric_name] = {
                'average': sum(metric_values) / len(metric_values),
                'min': min(metric_values),
                'max': max(metric_values),
                'count': len(metric_values),
                'latest': metric_values[-1]
            }
        
        # Group metrics by category
        grouped_metrics = {}
        for metric_name, metric_stats in stats.items():
            # Extract category from metric name (after performance. or before _duration)
            if metric_name.startswith('performance.'):
                category = metric_name.split('.')[1].split('_')[0]
            else:
                category = metric_name.split('_')[0]
            
            if category not in grouped_metrics:
                grouped_metrics[category] = {}
            
            grouped_metrics[category][metric_name] = metric_stats
        
        # Get time series data for charts
        charts = {}
        
        # Add chart for each category
        for category, metrics in grouped_metrics.items():
            # Get the top 5 metrics by latest value
            top_metrics = sorted(
                metrics.items(),
                key=lambda x: x[1]['latest'],
                reverse=True
            )[:5]
            
            # Create chart data
            chart_data = {}
            
            for metric_name, _ in top_metrics:
                # Get history for this metric
                history = get_metric_history(metric_name, 60)
                
                if history:
                    if 'labels' not in chart_data:
                        chart_data['labels'] = [item[0] for item in history]
                    
                    # Format metric name for display
                    display_name = metric_name.replace('performance.', '').replace('_duration', '')
                    
                    chart_data[display_name] = [item[1] for item in history]
            
            if chart_data:
                charts[category] = chart_data
        
        return {
            'name': self.name,
            'timestamp': datetime.now().isoformat(),
            'metrics': grouped_metrics,
            'charts': charts
        }
    
    def to_html(self) -> str:
        """
        Convert performance dashboard data to HTML.
        
        Returns:
            HTML representation of the performance dashboard
        """
        data = self.get_data()
        
        html = f"""
        <div class="dashboard performance-dashboard">
            <h2>Performance Dashboard</h2>
            <p>Last updated: {data['timestamp']}</p>
            
            <div class="dashboard-tabs">
                <div class="tab-buttons">
        """
        
        # Add tab buttons for each category
        for i, category in enumerate(data['metrics'].keys()):
            active = ' active' if i == 0 else ''
            html += f'<button class="tab-button{active}" data-tab="{category}">{category.title()}</button>'
        
        html += """
                </div>
                <div class="tab-content">
        """
        
        # Add tab content for each category
        for i, (category, metrics) in enumerate(data['metrics'].items()):
            active = ' active' if i == 0 else ''
            html += f"""
                    <div class="tab-pane{active}" id="tab-{category}">
                        <div class="dashboard-row">
                            <div class="dashboard-cell">
                                <h3>{category.title()} Performance</h3>
                                <div class="metric-chart" id="chart-{category}"></div>
                            </div>
                            
                            <div class="dashboard-cell">
                                <h3>Metrics</h3>
                                <table class="metrics-table">
                                    <thead>
                                        <tr>
                                            <th>Metric</th>
                                            <th>Latest</th>
                                            <th>Avg</th>
                                            <th>Min</th>
                                            <th>Max</th>
                                        </tr>
                                    </thead>
                                    <tbody>
            """
            
            # Add rows for each metric
            for metric_name, stats in metrics.items():
                display_name = metric_name.replace('performance.', '').replace('_duration', '')
                html += f"""
                                        <tr>
                                            <td>{display_name}</td>
                                            <td>{stats['latest']:.4f}s</td>
                                            <td>{stats['average']:.4f}s</td>
                                            <td>{stats['min']:.4f}s</td>
                                            <td>{stats['max']:.4f}s</td>
                                        </tr>
                """
            
            html += """
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
            """
        
        html += """
                </div>
            </div>
        </div>
        
        <script>
            // Tab functionality
            document.querySelectorAll('.tab-button').forEach(button => {
                button.addEventListener('click', () => {
                    // Deactivate all buttons and panes
                    document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
                    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                    
                    // Activate the clicked button and corresponding pane
                    button.classList.add('active');
                    document.getElementById('tab-' + button.dataset.tab).classList.add('active');
                });
            });
        </script>
        """
        
        # Add charts for each category
        for category, chart_data in data['charts'].items():
            # Create a dataset for each metric
            datasets = []
            colors = [
                'rgba(75, 192, 192, 1)',
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(153, 102, 255, 1)'
            ]
            
            for i, (metric_name, values) in enumerate(chart_data.items()):
                if metric_name != 'labels':
                    color = colors[i % len(colors)]
                    datasets.append(f"""{{
                        label: '{metric_name}',
                        data: {json.dumps(values)},
                        borderColor: '{color}',
                        backgroundColor: '{color.replace('1)', '0.2)')}',
                        borderWidth: 2,
                        fill: false
                    }}""")
            
            # Create the chart
            if chart_data.get('labels'):
                html += f"""
                <script>
                    // {category.title()} chart
                    var {category}Chart = new Chart(document.getElementById('chart-{category}').getContext('2d'), {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(chart_data['labels'])},
                            datasets: [{','.join(datasets)}]
                        }},
                        options: {{
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    title: {{
                                        display: true,
                                        text: 'Duration (s)'
                                    }}
                                }}
                            }},
                            animation: false,
                            responsive: true,
                            maintainAspectRatio: false
                        }}
                    }});
                </script>
                """
        
        return html


class AlertDashboard(Dashboard):
    """
    Dashboard for alerts.
    """
    
    def __init__(self):
        """Initialize the alert dashboard."""
        super().__init__("Alerts")
    
    def get_data(self) -> Dict[str, Any]:
        """
        Get alert dashboard data.
        
        Returns:
            Alert dashboard data
        """
        alert_manager = get_alert_manager()
        
        # Get active alerts
        active_alerts = alert_manager.get_active_alerts()
        
        # Format alerts for display
        formatted_alerts = []
        for alert in active_alerts:
            # Format timing information
            triggered_time = datetime.fromtimestamp(alert.triggered_at).isoformat() if alert.triggered_at else None
            acknowledged_time = datetime.fromtimestamp(alert.acknowledged_at).isoformat() if alert.acknowledged_at else None
            
            # Calculate duration
            duration = None
            if alert.triggered_at:
                duration = time.time() - alert.triggered_at
            
            formatted_alerts.append({
                'name': alert.name,
                'description': alert.description,
                'severity': alert.severity.value,
                'category': alert.category,
                'status': alert.status.value,
                'triggered_at': triggered_time,
                'acknowledged_at': acknowledged_time,
                'acknowledged_by': alert.acknowledged_by,
                'duration': duration,
                'details': alert.details
            })
        
        # Sort alerts by severity (critical first)
        severity_order = {
            'critical': 0,
            'error': 1,
            'warning': 2,
            'info': 3
        }
        
        formatted_alerts.sort(key=lambda a: (severity_order.get(a['severity'], 999), a['triggered_at']))
        
        # Get alert history
        alert_history = alert_manager.get_alert_history(20)
        
        # Format history for display
        formatted_history = []
        for entry in alert_history:
            formatted_history.append({
                'action': entry['action'],
                'alert': entry['alert'],
                'timestamp': datetime.fromtimestamp(entry['timestamp']).isoformat(),
                'details': entry.get('details', {})
            })
        
        # Get alert status counts
        alert_counts = {
            'total': len(alert_manager.alerts),
            'active': sum(1 for a in active_alerts if a.status == AlertStatus.ACTIVE),
            'acknowledged': sum(1 for a in active_alerts if a.status == AlertStatus.ACKNOWLEDGED),
            'resolved': len(alert_manager.alerts) - len(active_alerts),
            'by_severity': {
                'critical': sum(1 for a in active_alerts if a.severity.value == 'critical'),
                'error': sum(1 for a in active_alerts if a.severity.value == 'error'),
                'warning': sum(1 for a in active_alerts if a.severity.value == 'warning'),
                'info': sum(1 for a in active_alerts if a.severity.value == 'info')
            }
        }
        
        return {
            'name': self.name,
            'timestamp': datetime.now().isoformat(),
            'alerts': formatted_alerts,
            'history': formatted_history,
            'counts': alert_counts
        }
    
    def to_html(self) -> str:
        """
        Convert alert dashboard data to HTML.
        
        Returns:
            HTML representation of the alert dashboard
        """
        data = self.get_data()
        
        html = f"""
        <div class="dashboard alert-dashboard">
            <h2>Alert Dashboard</h2>
            <p>Last updated: {data['timestamp']}</p>
            
            <div class="dashboard-row">
                <div class="dashboard-cell alert-summary">
                    <div class="alert-stat">
                        <span class="alert-stat-value">{data['counts']['active']}</span>
                        <span class="alert-stat-label">Active</span>
                    </div>
                    <div class="alert-stat">
                        <span class="alert-stat-value">{data['counts']['acknowledged']}</span>
                        <span class="alert-stat-label">Acknowledged</span>
                    </div>
                    <div class="alert-stat">
                        <span class="alert-stat-value">{data['counts']['resolved']}</span>
                        <span class="alert-stat-label">Resolved</span>
                    </div>
                    <div class="alert-stat">
                        <span class="alert-stat-value">{data['counts']['total']}</span>
                        <span class="alert-stat-label">Total</span>
                    </div>
                </div>
                
                <div class="dashboard-cell severity-summary">
                    <div class="alert-stat severity-critical">
                        <span class="alert-stat-value">{data['counts']['by_severity']['critical']}</span>
                        <span class="alert-stat-label">Critical</span>
                    </div>
                    <div class="alert-stat severity-error">
                        <span class="alert-stat-value">{data['counts']['by_severity']['error']}</span>
                        <span class="alert-stat-label">Error</span>
                    </div>
                    <div class="alert-stat severity-warning">
                        <span class="alert-stat-value">{data['counts']['by_severity']['warning']}</span>
                        <span class="alert-stat-label">Warning</span>
                    </div>
                    <div class="alert-stat severity-info">
                        <span class="alert-stat-value">{data['counts']['by_severity']['info']}</span>
                        <span class="alert-stat-label">Info</span>
                    </div>
                </div>
            </div>
            
            <div class="dashboard-row">
                <div class="dashboard-cell">
                    <h3>Active Alerts</h3>
                    <div class="alert-list">
        """
        
        # Add active alerts
        if data['alerts']:
            for alert in data['alerts']:
                # Format duration
                duration_text = ''
                if alert['duration']:
                    if alert['duration'] < 60:
                        duration_text = f"{int(alert['duration'])} seconds"
                    elif alert['duration'] < 3600:
                        duration_text = f"{int(alert['duration'] / 60)} minutes"
                    else:
                        hours = int(alert['duration'] / 3600)
                        minutes = int((alert['duration'] % 3600) / 60)
                        duration_text = f"{hours} hours, {minutes} minutes"
                
                # Format details
                details_html = ''
                if alert['details']:
                    details_html = '<div class="alert-details">'
                    for key, value in alert['details'].items():
                        details_html += f'<div><b>{key}:</b> {value}</div>'
                    details_html += '</div>'
                
                html += f"""
                        <div class="alert-item severity-{alert['severity']}">
                            <div class="alert-header">
                                <span class="alert-name">{alert['name']}</span>
                                <span class="alert-severity">{alert['severity'].upper()}</span>
                                <span class="alert-status">{alert['status'].upper()}</span>
                            </div>
                            <div class="alert-content">
                                <div class="alert-description">{alert['description']}</div>
                                <div class="alert-info">
                                    <div><b>Category:</b> {alert['category']}</div>
                                    <div><b>Triggered:</b> {alert['triggered_at']} ({duration_text})</div>
                                    {f'<div><b>Acknowledged:</b> {alert["acknowledged_at"]} by {alert["acknowledged_by"] or "system"}</div>' if alert['acknowledged_at'] else ''}
                                </div>
                                {details_html}
                            </div>
                        </div>
                """
        else:
            html += '<div class="no-alerts">No active alerts</div>'
        
        html += """
                    </div>
                </div>
                
                <div class="dashboard-cell">
                    <h3>Recent Activity</h3>
                    <div class="alert-history">
                        <table class="history-table">
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>Action</th>
                                    <th>Alert</th>
                                    <th>Details</th>
                                </tr>
                            </thead>
                            <tbody>
        """
        
        # Add alert history
        for entry in data['history']:
            # Format details
            details_text = ''
            if entry['details']:
                details = []
                for key, value in entry['details'].items():
                    if key in ['severity', 'category', 'user', 'provider', 'status']:
                        details.append(f"{key}: {value}")
                details_text = ', '.join(details)
            
            html += f"""
                                <tr>
                                    <td>{entry['timestamp']}</td>
                                    <td>{entry['action'].replace('_', ' ').title()}</td>
                                    <td>{entry['alert']}</td>
                                    <td>{details_text}</td>
                                </tr>
            """
        
        html += """
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
            .alert-summary, .severity-summary {
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
            }
            
            .alert-stat {
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 15px;
                border-radius: 8px;
                background-color: #f5f5f5;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .alert-stat-value {
                font-size: 24px;
                font-weight: bold;
            }
            
            .alert-stat-label {
                margin-top: 5px;
                font-size: 14px;
                color: #666;
            }
            
            .severity-critical {
                background-color: #fee;
                border-left: 4px solid #d00;
            }
            
            .severity-error {
                background-color: #fff0f0;
                border-left: 4px solid #f44;
            }
            
            .severity-warning {
                background-color: #ffd;
                border-left: 4px solid #ed0;
            }
            
            .severity-info {
                background-color: #eef;
                border-left: 4px solid #44f;
            }
            
            .alert-item {
                margin-bottom: 10px;
                border-radius: 4px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            
            .alert-header {
                display: flex;
                justify-content: space-between;
                padding: 8px 12px;
                background-color: #f0f0f0;
            }
            
            .alert-content {
                padding: 12px;
                background-color: white;
            }
            
            .alert-description {
                margin-bottom: 8px;
                font-weight: 500;
            }
            
            .alert-info {
                font-size: 13px;
                color: #666;
                margin-bottom: 8px;
            }
            
            .alert-details {
                margin-top: 8px;
                padding: 8px;
                background-color: #f9f9f9;
                border-radius: 4px;
                font-size: 12px;
            }
            
            .history-table {
                width: 100%;
                border-collapse: collapse;
            }
            
            .history-table th, .history-table td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            
            .history-table th {
                background-color: #f5f5f5;
                font-weight: 500;
            }
            
            .no-alerts {
                padding: 20px;
                text-align: center;
                color: #888;
                font-style: italic;
            }
        </style>
        """
        
        return html


class DashboardManager:
    """
    Manages multiple monitoring dashboards.
    """
    
    def __init__(self):
        """Initialize the dashboard manager."""
        self.dashboards = {}
        self.logger = logging.getLogger('monitoring.dashboard')
        
        # Register standard dashboards
        self.register_dashboard('system', SystemDashboard())
        self.register_dashboard('performance', PerformanceDashboard())
        self.register_dashboard('alerts', AlertDashboard())
    
    def register_dashboard(self, name: str, dashboard: Dashboard):
        """
        Register a dashboard.
        
        Args:
            name: Dashboard name
            dashboard: Dashboard instance
        """
        self.dashboards[name] = dashboard
        self.logger.info(f"Registered dashboard: {name}")
    
    def get_dashboard(self, name: str) -> Optional[Dashboard]:
        """
        Get a dashboard by name.
        
        Args:
            name: Dashboard name
            
        Returns:
            Dashboard instance or None if not found
        """
        return self.dashboards.get(name)
    
    def get_all_dashboards(self) -> Dict[str, Dashboard]:
        """
        Get all registered dashboards.
        
        Returns:
            Dictionary mapping dashboard names to instances
        """
        return self.dashboards.copy()
    
    def render_dashboard(self, name: str, format: str = 'html') -> str:
        """
        Render a dashboard in the specified format.
        
        Args:
            name: Dashboard name
            format: Output format ('html' or 'json')
            
        Returns:
            Rendered dashboard
            
        Raises:
            ValueError: If dashboard not found or format not supported
        """
        dashboard = self.get_dashboard(name)
        if not dashboard:
            raise ValueError(f"Dashboard not found: {name}")
        
        if format == 'html':
            return dashboard.to_html()
        elif format == 'json':
            return dashboard.to_json()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def render_dashboard_index(self) -> str:
        """
        Render an index page for all dashboards.
        
        Returns:
            HTML index page
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>zgen AI Agent - Monitoring Dashboards</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    line-height: 1.5;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f9f9f9;
                }
                
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                header {
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                
                header h1 {
                    margin: 0;
                    font-size: 24px;
                }
                
                nav {
                    background-color: #34495e;
                    padding: 10px 20px;
                }
                
                nav ul {
                    list-style: none;
                    margin: 0;
                    padding: 0;
                    display: flex;
                }
                
                nav li {
                    margin-right: 20px;
                }
                
                nav a {
                    color: white;
                    text-decoration: none;
                    font-weight: 500;
                    opacity: 0.8;
                    transition: opacity 0.2s;
                }
                
                nav a:hover {
                    opacity: 1;
                }
                
                nav a.active {
                    opacity: 1;
                    border-bottom: 2px solid white;
                }
                
                .dashboard {
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    padding: 20px;
                    margin-bottom: 30px;
                }
                
                .dashboard h2 {
                    margin-top: 0;
                    margin-bottom: 10px;
                    font-size: 20px;
                    color: #2c3e50;
                }
                
                .dashboard p {
                    color: #7f8c8d;
                    font-size: 14px;
                    margin-bottom: 20px;
                }
                
                .dashboard-row {
                    display: flex;
                    flex-wrap: wrap;
                    margin: 0 -10px;
                }
                
                .dashboard-cell {
                    flex: 1;
                    padding: 10px;
                    min-width: 300px;
                }
                
                .metric-chart {
                    height: 200px;
                    margin-bottom: 15px;
                }
                
                .metric-values {
                    font-size: 14px;
                }
                
                .metric-values div {
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                }
                
                .dashboard-tabs .tab-buttons {
                    display: flex;
                    margin-bottom: 15px;
                    border-bottom: 1px solid #ddd;
                }
                
                .dashboard-tabs .tab-button {
                    padding: 8px 16px;
                    background: none;
                    border: none;
                    cursor: pointer;
                    font-size: 14px;
                    opacity: 0.7;
                    transition: opacity 0.2s;
                }
                
                .dashboard-tabs .tab-button.active {
                    opacity: 1;
                    border-bottom: 2px solid #3498db;
                }
                
                .dashboard-tabs .tab-content .tab-pane {
                    display: none;
                }
                
                .dashboard-tabs .tab-content .tab-pane.active {
                    display: block;
                }
                
                .metrics-table {
                    width: 100%;
                    border-collapse: collapse;
                }
                
                .metrics-table th, .metrics-table td {
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #eee;
                    font-size: 14px;
                }
                
                .metrics-table th {
                    font-weight: 500;
                    color: #666;
                }
                
                footer {
                    margin-top: 30px;
                    padding: 20px;
                    text-align: center;
                    font-size: 14px;
                    color: #7f8c8d;
                    border-top: 1px solid #eee;
                }
                
                #refresh-status {
                    margin-left: 10px;
                    font-size: 14px;
                    color: #7f8c8d;
                }
                
                .auto-refresh {
                    margin-left: auto;
                    display: flex;
                    align-items: center;
                }
                
                .auto-refresh label {
                    margin-right: 10px;
                    color: white;
                    font-size: 14px;
                }
                
                .auto-refresh select {
                    padding: 4px;
                    border-radius: 4px;
                    border: none;
                }
            </style>
        </head>
        <body>
            <header>
                <div class="container">
                    <h1>zgen AI Agent - Monitoring Dashboards</h1>
                </div>
            </header>
            
            <nav>
                <div class="container">
                    <ul>
        """
        
        # Add dashboard navigation links
        for name, dashboard in self.dashboards.items():
            html += f'<li><a href="#" data-dashboard="{name}" class="dashboard-link">{dashboard.name}</a></li>'
        
        html += """
                        <li class="auto-refresh">
                            <label for="refresh-interval">Auto refresh:</label>
                            <select id="refresh-interval">
                                <option value="0">Off</option>
                                <option value="5">5 seconds</option>
                                <option value="10" selected>10 seconds</option>
                                <option value="30">30 seconds</option>
                                <option value="60">1 minute</option>
                                <option value="300">5 minutes</option>
                            </select>
                            <span id="refresh-status"></span>
                        </li>
                    </ul>
                </div>
            </nav>
            
            <div class="container">
                <div id="dashboard-content">
                    <!-- Dashboard content will be loaded here -->
                    <div class="dashboard">
                        <h2>Welcome to zgen AI Agent Monitoring</h2>
                        <p>Select a dashboard from the navigation bar above to view monitoring data.</p>
                    </div>
                </div>
            </div>
            
            <footer>
                <div class="container">
                    <p>zgen AI Agent - Local Monitoring Dashboard</p>
                </div>
            </footer>
            
            <script>
                // Dashboard navigation
                const dashboardLinks = document.querySelectorAll('.dashboard-link');
                const dashboardContent = document.getElementById('dashboard-content');
                const refreshInterval = document.getElementById('refresh-interval');
                const refreshStatus = document.getElementById('refresh-status');
                
                let currentDashboard = null;
                let refreshTimer = null;
                let lastRefreshTime = null;
                
                // Load a dashboard
                function loadDashboard(name) {
                    fetch(`/monitoring/dashboard/${name}`)
                        .then(response => response.text())
                        .then(html => {
                            dashboardContent.innerHTML = html;
                            currentDashboard = name;
                            
                            // Update active link
                            dashboardLinks.forEach(link => {
                                if (link.dataset.dashboard === name) {
                                    link.classList.add('active');
                                } else {
                                    link.classList.remove('active');
                                }
                            });
                            
                            // Update refresh time
                            lastRefreshTime = new Date();
                            updateRefreshStatus();
                        })
                        .catch(error => {
                            console.error('Error loading dashboard:', error);
                            dashboardContent.innerHTML = `
                                <div class="dashboard">
                                    <h2>Error</h2>
                                    <p>Failed to load dashboard: ${error.message}</p>
                                </div>
                            `;
                        });
                }
                
                // Set up dashboard navigation
                dashboardLinks.forEach(link => {
                    link.addEventListener('click', (e) => {
                        e.preventDefault();
                        loadDashboard(link.dataset.dashboard);
                    });
                });
                
                // Auto-refresh functionality
                refreshInterval.addEventListener('change', () => {
                    // Clear existing timer
                    if (refreshTimer) {
                        clearInterval(refreshTimer);
                        refreshTimer = null;
                    }
                    
                    // Set up new timer if needed
                    const seconds = parseInt(refreshInterval.value);
                    if (seconds > 0 && currentDashboard) {
                        refreshTimer = setInterval(() => {
                            loadDashboard(currentDashboard);
                        }, seconds * 1000);
                    }
                    
                    updateRefreshStatus();
                });
                
                // Update refresh status display
                function updateRefreshStatus() {
                    const seconds = parseInt(refreshInterval.value);
                    if (seconds > 0) {
                        if (lastRefreshTime) {
                            const timeSince = Math.round((new Date() - lastRefreshTime) / 1000);
                            refreshStatus.textContent = `Last refreshed ${timeSince}s ago`;
                        }
                    } else {
                        refreshStatus.textContent = '';
                    }
                }
                
                // Update refresh status display every second
                setInterval(updateRefreshStatus, 1000);
                
                // Load the first dashboard by default
                if (dashboardLinks.length > 0) {
                    loadDashboard(dashboardLinks[0].dataset.dashboard);
                }
            </script>
        </body>
        </html>
        """
        
        return html


# Singleton instance
_dashboard_manager = None

def get_dashboard_manager():
    """
    Get the singleton dashboard manager instance.
    
    Returns:
        DashboardManager instance
    """
    global _dashboard_manager
    if _dashboard_manager is None:
        _dashboard_manager = DashboardManager()
    return _dashboard_manager


def get_dashboard(name: str) -> Optional[Dashboard]:
    """
    Get a dashboard by name.
    
    Args:
        name: Dashboard name
        
    Returns:
        Dashboard instance or None if not found
    """
    manager = get_dashboard_manager()
    return manager.get_dashboard(name)


def render_dashboard(name: str, format: str = 'html') -> str:
    """
    Render a dashboard in the specified format.
    
    Args:
        name: Dashboard name
        format: Output format ('html' or 'json')
        
    Returns:
        Rendered dashboard
        
    Raises:
        ValueError: If dashboard not found or format not supported
    """
    manager = get_dashboard_manager()
    return manager.render_dashboard(name, format)


def render_dashboard_index() -> str:
    """
    Render an index page for all dashboards.
    
    Returns:
        HTML index page
    """
    manager = get_dashboard_manager()
    return manager.render_dashboard_index()