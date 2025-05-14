"""
Monitoring API Endpoints
-------------------
This module provides API endpoints for the monitoring system.
"""

import json
import time
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from fastapi.responses import HTMLResponse, JSONResponse

from monitoring.metrics import (
    get_all_metrics,
    get_metric_history,
    get_metric_average,
    record_metric
)
from monitoring.system_monitor import get_system_info, get_system_monitor
from monitoring.performance import get_profiler, report_stats
from monitoring.alerting import (
    get_alert_manager,
    AlertSeverity,
    trigger_alert,
    start_alerting,
    stop_alerting
)
from monitoring.dashboards.dashboard import (
    get_dashboard,
    render_dashboard,
    render_dashboard_index
)

# Create a router
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/")
async def get_monitoring_status():
    """Get the status of the monitoring system."""
    # Get system info
    system_info = get_system_info()
    
    # Get alerting info
    alert_manager = get_alert_manager()
    alert_status = alert_manager.get_status()
    
    # Get metrics info
    metrics = get_all_metrics()
    metric_count = len(metrics)
    
    return {
        "status": "active",
        "system_info": system_info,
        "alerts": alert_status,
        "metrics": {
            "count": metric_count,
            "categories": list(set(name.split('.')[0] for name in metrics.keys() if '.' in name))
        }
    }


@router.get("/metrics")
async def get_metrics(
    category: Optional[str] = None,
    limit: int = Query(100, gt=0, le=1000)
):
    """
    Get all metrics or metrics for a specific category.
    
    Args:
        category: Optional category filter
        limit: Maximum number of values to return per metric
    """
    metrics = get_all_metrics()
    
    # Filter by category if specified
    if category:
        filtered_metrics = {}
        prefix = f"{category}."
        for name, values in metrics.items():
            if name.startswith(prefix):
                # Limit the number of values
                filtered_metrics[name] = values[-limit:] if limit > 0 else values
        return filtered_metrics
    else:
        # Limit the number of values for all metrics
        return {name: values[-limit:] if limit > 0 else values for name, values in metrics.items()}


@router.get("/metrics/{metric_name}")
async def get_metric(
    metric_name: str = Path(..., description="Name of the metric to retrieve"),
    limit: int = Query(100, gt=0, le=1000)
):
    """
    Get history for a specific metric.
    
    Args:
        metric_name: Metric name
        limit: Maximum number of values to return
    """
    history = get_metric_history(metric_name, limit)
    if not history:
        raise HTTPException(status_code=404, detail=f"Metric not found: {metric_name}")
    
    return {"name": metric_name, "values": history}


@router.post("/metrics")
async def record_custom_metric(
    name: str,
    value: float,
    category: Optional[str] = None
):
    """
    Record a custom metric.
    
    Args:
        name: Metric name
        value: Metric value
        category: Optional metric category
    """
    record_metric(name, value, category)
    return {"status": "success", "message": f"Recorded metric: {name}={value}"}


@router.get("/alerts")
async def get_alerts(
    active_only: bool = Query(True, description="Only return active alerts")
):
    """
    Get all alerts or active alerts.
    
    Args:
        active_only: Whether to return only active alerts
    """
    alert_manager = get_alert_manager()
    
    if active_only:
        alerts = alert_manager.get_active_alerts()
        return {
            "count": len(alerts),
            "alerts": [alert.to_dict() for alert in alerts]
        }
    else:
        return {
            "count": len(alert_manager.alerts),
            "alerts": {name: alert.to_dict() for name, alert in alert_manager.alerts.items()}
        }


@router.get("/alerts/history")
async def get_alert_history(
    limit: int = Query(100, gt=0, le=1000)
):
    """
    Get alert history.
    
    Args:
        limit: Maximum number of entries to return
    """
    alert_manager = get_alert_manager()
    history = alert_manager.get_alert_history(limit)
    
    return {"count": len(history), "history": history}


@router.post("/alerts")
async def create_alert(
    name: str,
    description: str,
    severity: str = "warning",
    category: str = "custom",
    details: Optional[Dict[str, Any]] = None
):
    """
    Create and trigger a new alert.
    
    Args:
        name: Alert name
        description: Alert description
        severity: Alert severity (info, warning, error, critical)
        category: Alert category
        details: Additional details about the alert
    """
    # Convert severity string to enum
    try:
        severity_enum = AlertSeverity[severity.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity: {severity}. Must be one of: info, warning, error, critical"
        )
    
    # Trigger the alert
    alert = trigger_alert(
        name=name,
        description=description,
        severity=severity_enum,
        category=category,
        details=details
    )
    
    return {"status": "success", "alert": alert.to_dict()}


@router.put("/alerts/{name}/acknowledge")
async def acknowledge_alert(
    name: str = Path(..., description="Name of the alert to acknowledge"),
    user: Optional[str] = None
):
    """
    Acknowledge an alert.
    
    Args:
        name: Alert name
        user: User who acknowledged the alert
    """
    alert_manager = get_alert_manager()
    result = alert_manager.acknowledge_alert(name, user)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Alert not found or not active: {name}")
    
    return {"status": "success", "message": f"Alert acknowledged: {name}"}


@router.put("/alerts/{name}/resolve")
async def resolve_alert(
    name: str = Path(..., description="Name of the alert to resolve")
):
    """
    Resolve an alert.
    
    Args:
        name: Alert name
    """
    alert_manager = get_alert_manager()
    result = alert_manager.resolve_alert(name)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Alert not found or already resolved: {name}")
    
    return {"status": "success", "message": f"Alert resolved: {name}"}


@router.put("/alerts/{name}/silence")
async def silence_alert(
    name: str = Path(..., description="Name of the alert to silence"),
    silence: bool = True
):
    """
    Silence or unsilence an alert.
    
    Args:
        name: Alert name
        silence: Whether to silence the alert
    """
    alert_manager = get_alert_manager()
    result = alert_manager.silence_alert(name, silence)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Alert not found: {name}")
    
    return {
        "status": "success",
        "message": f"Alert {'silenced' if silence else 'unsilenced'}: {name}"
    }


@router.get("/dashboard")
async def get_dashboard_index():
    """Get the dashboard index page."""
    html = render_dashboard_index()
    return HTMLResponse(content=html)


@router.get("/dashboard/{name}")
async def get_dashboard_by_name(
    name: str = Path(..., description="Dashboard name"),
    format: str = Query("html", description="Output format (html or json)")
):
    """
    Get a specific dashboard.
    
    Args:
        name: Dashboard name
        format: Output format (html or json)
    """
    try:
        content = render_dashboard(name, format)
        
        if format == "html":
            return HTMLResponse(content=content)
        else:
            return JSONResponse(content=json.loads(content))
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/performance")
async def get_performance_stats(
    category: Optional[str] = None
):
    """
    Get performance statistics.
    
    Args:
        category: Optional category filter
    """
    stats = report_stats(category)
    return stats


@router.post("/control/start")
async def start_monitoring_system():
    """Start the monitoring and alerting system."""
    try:
        # Start system monitoring
        monitor = get_system_monitor()
        monitor.start()
        
        # Start alerting
        start_alerting()
        
        return {"status": "success", "message": "Monitoring system started"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.post("/control/stop")
async def stop_monitoring_system():
    """Stop the monitoring and alerting system."""
    try:
        # Stop system monitoring
        monitor = get_system_monitor()
        monitor.stop()
        
        # Stop alerting
        stop_alerting()
        
        return {"status": "success", "message": "Monitoring system stopped"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")