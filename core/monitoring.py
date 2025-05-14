"""
Core Monitoring Integration
------------------------
This module provides integration between the core agent and the monitoring system,
allowing the agent to report performance metrics and health status.
"""

import time
import logging
from typing import Dict, Any, Optional, List, Callable, Union

# Import monitoring components if available
try:
    from monitoring.metrics import record_metric
    from monitoring.performance import track, track_async, track_context
    from monitoring.alerting import trigger_alert, AlertSeverity
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    # Define placeholders for tracking decorators
    def track(name=None, log_level=logging.DEBUG):
        def decorator(func):
            return func
        return decorator
    
    def track_async(name=None, log_level=logging.DEBUG):
        def decorator(func):
            return func
        return decorator
    
    def track_context(name, log_level=logging.DEBUG):
        class DummyContext:
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        
        return DummyContext()


class AgentMonitor:
    """
    Monitoring integration for the Scout agent.
    Tracks performance metrics, task execution, and agent health.
    """
    
    def __init__(self):
        """Initialize the agent monitor."""
        self.logger = logging.getLogger("agent.monitor")
        self.task_execution_times = {}
        self.last_health_check = time.time()
        self.healthy = True
        self.metrics_enabled = MONITORING_AVAILABLE
    
    def record_task_start(self, task_id: str):
        """
        Record the start time of a task.
        
        Args:
            task_id: Task ID
        """
        self.task_execution_times[task_id] = time.time()
        
        if self.metrics_enabled:
            record_metric("tasks.started", 1, "agent")
    
    def record_task_complete(self, task_id: str, success: bool = True):
        """
        Record the completion of a task.
        
        Args:
            task_id: Task ID
            success: Whether the task completed successfully
        """
        start_time = self.task_execution_times.get(task_id)
        if start_time:
            # Calculate execution time
            execution_time = time.time() - start_time
            
            if self.metrics_enabled:
                # Record task execution time
                record_metric("tasks.execution_time", execution_time, "agent")
                
                # Record success/failure
                if success:
                    record_metric("tasks.completed", 1, "agent")
                else:
                    record_metric("tasks.failed", 1, "agent")
            
            # Clean up
            del self.task_execution_times[task_id]
    
    def record_api_request(self, endpoint: str):
        """
        Record an API request.
        
        Args:
            endpoint: API endpoint
        """
        if self.metrics_enabled:
            record_metric("api.requests", 1, "agent")
            record_metric(f"api.{endpoint}.requests", 1, "agent")
    
    def record_api_response_time(self, endpoint: str, response_time: float):
        """
        Record API response time.
        
        Args:
            endpoint: API endpoint
            response_time: Response time in seconds
        """
        if self.metrics_enabled:
            record_metric("api.response_time", response_time, "agent")
            record_metric(f"api.{endpoint}.response_time", response_time, "agent")
    
    def record_memory_usage(self, usage_bytes: int):
        """
        Record agent memory usage.
        
        Args:
            usage_bytes: Memory usage in bytes
        """
        if self.metrics_enabled:
            record_metric("agent.memory_usage", usage_bytes, "agent")
    
    def record_token_usage(self, prompt_tokens: int, completion_tokens: int, model: str):
        """
        Record token usage for LLM interactions.
        
        Args:
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            model: LLM model name
        """
        if self.metrics_enabled:
            record_metric("llm.prompt_tokens", prompt_tokens, "agent")
            record_metric("llm.completion_tokens", completion_tokens, "agent")
            record_metric("llm.total_tokens", prompt_tokens + completion_tokens, "agent")
            record_metric(f"llm.models.{model}.tokens", prompt_tokens + completion_tokens, "agent")
    
    def record_error(self, component: str, error_type: str, message: str, severity: str = "error"):
        """
        Record an error.
        
        Args:
            component: Component where the error occurred
            error_type: Type of error
            message: Error message
            severity: Error severity (info, warning, error, critical)
        """
        self.logger.error(f"Error in {component}: {error_type} - {message}")
        
        if self.metrics_enabled:
            # Record error count
            record_metric("errors.total", 1, "agent")
            record_metric(f"errors.{component}", 1, "agent")
            
            # Trigger an alert
            try:
                from monitoring.alerting import AlertSeverity
                # Convert severity string to enum
                severity_enum = getattr(AlertSeverity, severity.upper(), AlertSeverity.ERROR)
                
                trigger_alert(
                    name=f"{component}_{error_type}",
                    description=f"Error in {component}: {message}",
                    severity=severity_enum,
                    category="agent_errors",
                    details={
                        "component": component,
                        "error_type": error_type,
                        "message": message
                    }
                )
            except ImportError:
                # Alerting system not available
                pass
            except Exception as e:
                self.logger.error(f"Failed to trigger alert: {e}")
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check agent health.
        
        Returns:
            Dictionary with health status
        """
        now = time.time()
        
        # Only run health check every 60 seconds
        if now - self.last_health_check < 60:
            return {
                "healthy": self.healthy,
                "last_check": self.last_health_check
            }
        
        self.last_health_check = now
        
        # Check various health indicators
        # TODO: Implement actual health checks
        
        return {
            "healthy": self.healthy,
            "last_check": self.last_health_check
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get agent metrics.
        
        Returns:
            Dictionary with agent metrics
        """
        if not self.metrics_enabled:
            return {
                "metrics_enabled": False,
                "message": "Monitoring system not available"
            }
        
        try:
            from monitoring.metrics import get_all_metrics
            
            # Get agent-specific metrics
            all_metrics = get_all_metrics()
            agent_metrics = {}
            
            for name, values in all_metrics.items():
                if name.startswith("agent.") or name.startswith("tasks.") or name.startswith("llm.") or name.startswith("api."):
                    agent_metrics[name] = values
            
            return {
                "metrics_enabled": True,
                "metrics": agent_metrics
            }
        except ImportError:
            return {
                "metrics_enabled": False,
                "message": "Monitoring metrics module not available"
            }
        except Exception as e:
            return {
                "metrics_enabled": True,
                "error": str(e),
                "message": "Failed to retrieve metrics"
            }


# Singleton instance
_agent_monitor = None

def get_agent_monitor() -> AgentMonitor:
    """
    Get the singleton agent monitor instance.
    
    Returns:
        AgentMonitor instance
    """
    global _agent_monitor
    if _agent_monitor is None:
        _agent_monitor = AgentMonitor()
    return _agent_monitor