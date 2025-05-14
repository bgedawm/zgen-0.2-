"""
Alerting System
-----------
This module provides an alerting system that can notify about critical issues,
system events, and performance problems.
"""

import os
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union

from monitoring.metrics import get_metrics_collector, register_callback
from core.integrations.notification_providers import (
    get_notification_provider,
    SlackProvider,
    EmailProvider,
    DiscordProvider
)


class AlertSeverity(Enum):
    """Alert severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert statuses."""
    
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Alert:
    """
    Represents an alert that can be triggered based on certain conditions.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        category: str = "general",
        auto_resolve: bool = True,
        resolve_after: int = 300,  # 5 minutes
        reminder_interval: int = 1800,  # 30 minutes
        silenced: bool = False
    ):
        """
        Initialize an alert.
        
        Args:
            name: Alert name
            description: Alert description
            severity: Alert severity level
            category: Alert category
            auto_resolve: Whether to auto-resolve the alert when condition is no longer true
            resolve_after: Seconds after which to auto-resolve the alert
            reminder_interval: Seconds between reminder notifications
            silenced: Whether the alert is silenced (no notifications)
        """
        self.name = name
        self.description = description
        self.severity = severity
        self.category = category
        self.auto_resolve = auto_resolve
        self.resolve_after = resolve_after
        self.reminder_interval = reminder_interval
        self.silenced = silenced
        
        # Alert state
        self.status = AlertStatus.RESOLVED
        self.triggered_at = None
        self.resolved_at = None
        self.acknowledged_at = None
        self.acknowledged_by = None
        self.last_notification = None
        self.trigger_count = 0
        self.details = None
    
    def trigger(self, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Trigger the alert.
        
        Args:
            details: Additional details about the alert
            
        Returns:
            True if the alert was newly triggered, False if already active
        """
        now = time.time()
        
        # If already active, only update details
        if self.status == AlertStatus.ACTIVE or self.status == AlertStatus.ACKNOWLEDGED:
            self.details = details
            return False
        
        # Trigger the alert
        self.status = AlertStatus.ACTIVE
        self.triggered_at = now
        self.resolved_at = None
        self.last_notification = None
        self.trigger_count += 1
        self.details = details
        
        return True
    
    def acknowledge(self, user: Optional[str] = None) -> bool:
        """
        Acknowledge the alert.
        
        Args:
            user: User who acknowledged the alert
            
        Returns:
            True if the alert was acknowledged, False otherwise
        """
        if self.status != AlertStatus.ACTIVE:
            return False
        
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = time.time()
        self.acknowledged_by = user
        
        return True
    
    def resolve(self) -> bool:
        """
        Resolve the alert.
        
        Returns:
            True if the alert was resolved, False otherwise
        """
        if self.status == AlertStatus.RESOLVED:
            return False
        
        self.status = AlertStatus.RESOLVED
        self.resolved_at = time.time()
        
        return True
    
    def should_notify(self) -> bool:
        """
        Check if a notification should be sent for this alert.
        
        Returns:
            True if a notification should be sent, False otherwise
        """
        if self.silenced:
            return False
        
        now = time.time()
        
        # Never notified before
        if self.last_notification is None:
            return True
        
        # For acknowledged alerts, only send reminders if interval has passed
        if self.status == AlertStatus.ACKNOWLEDGED:
            return (now - self.last_notification) >= self.reminder_interval
        
        # For active alerts, send reminders based on severity and interval
        if self.status == AlertStatus.ACTIVE:
            # For critical alerts, send more frequent reminders
            if self.severity == AlertSeverity.CRITICAL:
                return (now - self.last_notification) >= (self.reminder_interval / 2)
            
            # For other severities, use standard reminder interval
            return (now - self.last_notification) >= self.reminder_interval
        
        return False
    
    def should_auto_resolve(self) -> bool:
        """
        Check if the alert should be auto-resolved.
        
        Returns:
            True if the alert should be auto-resolved, False otherwise
        """
        if not self.auto_resolve:
            return False
        
        if self.status == AlertStatus.RESOLVED:
            return False
        
        now = time.time()
        
        # Auto-resolve after the specified time
        return (now - self.triggered_at) >= self.resolve_after
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the alert to a dictionary.
        
        Returns:
            Dictionary representation of the alert
        """
        return {
            'name': self.name,
            'description': self.description,
            'severity': self.severity.value,
            'category': self.category,
            'status': self.status.value,
            'triggered_at': self.triggered_at,
            'resolved_at': self.resolved_at,
            'acknowledged_at': self.acknowledged_at,
            'acknowledged_by': self.acknowledged_by,
            'trigger_count': self.trigger_count,
            'details': self.details,
            'auto_resolve': self.auto_resolve,
            'resolve_after': self.resolve_after,
            'silenced': self.silenced
        }


class AlertRule:
    """
    Represents a rule that can trigger an alert based on conditions.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        condition: Callable[[], bool],
        alert: Alert,
        check_interval: int = 60  # Check every minute by default
    ):
        """
        Initialize an alert rule.
        
        Args:
            name: Rule name
            description: Rule description
            condition: Function that returns True if the alert should be triggered
            alert: Alert to trigger
            check_interval: How often to check the condition (in seconds)
        """
        self.name = name
        self.description = description
        self.condition = condition
        self.alert = alert
        self.check_interval = check_interval
        
        # Rule state
        self.last_check = 0
        self.last_value = None
    
    def check(self) -> bool:
        """
        Check the rule condition and trigger the alert if needed.
        
        Returns:
            True if the alert was triggered or is active, False otherwise
        """
        now = time.time()
        
        # Skip if not time to check yet
        if now - self.last_check < self.check_interval:
            return self.alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]
        
        self.last_check = now
        
        try:
            # Check the condition
            result = self.condition()
            self.last_value = result
            
            if result:
                # Condition is true, trigger the alert
                self.alert.trigger()
                return True
            else:
                # Condition is false, maybe resolve the alert
                if self.alert.auto_resolve:
                    self.alert.resolve()
                
                return False
        
        except Exception as e:
            # Log the error
            logging.getLogger('monitoring.alerting').error(
                f"Error checking alert rule '{self.name}': {e}",
                exc_info=True
            )
            
            # Don't trigger the alert on errors
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the rule to a dictionary.
        
        Returns:
            Dictionary representation of the rule
        """
        return {
            'name': self.name,
            'description': self.description,
            'check_interval': self.check_interval,
            'last_check': self.last_check,
            'last_value': self.last_value,
            'alert': self.alert.to_dict()
        }


class MetricAlertRule:
    """
    A specialized alert rule that monitors a metric value.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        metric_name: str,
        threshold: float,
        operator: str = '>',
        duration: int = 0,  # How long the condition must be true (in seconds)
        alert: Alert = None,
        check_interval: int = 60,  # Check every minute by default
        severity: AlertSeverity = AlertSeverity.WARNING,
        category: str = "metrics"
    ):
        """
        Initialize a metric alert rule.
        
        Args:
            name: Rule name
            description: Rule description
            metric_name: Name of the metric to monitor
            threshold: Threshold value to compare against
            operator: Comparison operator ('>', '>=', '<', '<=', '==', '!=')
            duration: How long the condition must be true (in seconds)
            alert: Alert to trigger (created automatically if not provided)
            check_interval: How often to check the condition (in seconds)
            severity: Alert severity (if creating alert automatically)
            category: Alert category (if creating alert automatically)
        """
        self.name = name
        self.description = description
        self.metric_name = metric_name
        self.threshold = threshold
        self.operator = operator
        self.duration = duration
        
        # Create alert if not provided
        if alert is None:
            self.alert = Alert(
                name=f"Metric {name}",
                description=description,
                severity=severity,
                category=category
            )
        else:
            self.alert = alert
        
        # Create the condition function
        self.condition = self._create_condition()
        
        # Create the underlying rule
        self.rule = AlertRule(
            name=name,
            description=description,
            condition=self.condition,
            alert=self.alert,
            check_interval=check_interval
        )
        
        # Register a callback for the metric
        register_callback(metric_name, self._metric_callback)
        
        # State for duration-based alerting
        self.violation_start = None
    
    def _create_condition(self) -> Callable[[], bool]:
        """
        Create a condition function based on the metric and threshold.
        
        Returns:
            Function that returns True if the condition is met
        """
        def condition():
            # Get the current value of the metric
            from monitoring.metrics import get_metric_average
            value = get_metric_average(self.metric_name, 60)  # Look at the last minute
            
            if value is None:
                return False
            
            # Check if the value violates the threshold
            violation = False
            
            if self.operator == '>':
                violation = value > self.threshold
            elif self.operator == '>=':
                violation = value >= self.threshold
            elif self.operator == '<':
                violation = value < self.threshold
            elif self.operator == '<=':
                violation = value <= self.threshold
            elif self.operator == '==':
                violation = value == self.threshold
            elif self.operator == '!=':
                violation = value != self.threshold
            
            # Update duration tracking
            now = time.time()
            
            if violation:
                if self.violation_start is None:
                    self.violation_start = now
                
                # Check if violation has lasted long enough
                if self.duration > 0:
                    return (now - self.violation_start) >= self.duration
                else:
                    return True
            else:
                # Reset violation tracking
                self.violation_start = None
                return False
        
        return condition
    
    def _metric_callback(self, metric_name, value):
        """
        Callback function for when a metric value is updated.
        
        Args:
            metric_name: Name of the updated metric
            value: New metric value
        """
        # Check the rule immediately if the metric we care about was updated
        if metric_name == self.metric_name:
            self.rule.check()
    
    def check(self) -> bool:
        """
        Check the rule condition and trigger the alert if needed.
        
        Returns:
            True if the alert was triggered or is active, False otherwise
        """
        return self.rule.check()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the metric rule to a dictionary.
        
        Returns:
            Dictionary representation of the metric rule
        """
        rule_dict = self.rule.to_dict()
        rule_dict.update({
            'metric_name': self.metric_name,
            'threshold': self.threshold,
            'operator': self.operator,
            'duration': self.duration,
            'violation_start': self.violation_start
        })
        return rule_dict


class AlertManager:
    """
    Manages alerts, rules, and notifications.
    """
    
    def __init__(self):
        """Initialize the alert manager."""
        self.alerts = {}
        self.rules = {}
        self.notification_providers = {}
        self.alert_history = []
        
        # Thread for checking rules
        self.running = False
        self.check_thread = None
        
        # Logger
        self.logger = logging.getLogger('monitoring.alerting')
        
        # Load providers
        self._load_notification_providers()
    
    def _load_notification_providers(self):
        """Load notification providers from configuration."""
        try:
            # Get default notification provider
            provider = get_notification_provider()
            self.notification_providers['default'] = provider
            
            # Try to load specific providers
            try:
                slack = get_notification_provider('slack')
                self.notification_providers['slack'] = slack
            except:
                pass
            
            try:
                email = get_notification_provider('email')
                self.notification_providers['email'] = email
            except:
                pass
            
            try:
                discord = get_notification_provider('discord')
                self.notification_providers['discord'] = discord
            except:
                pass
        except Exception as e:
            self.logger.error(f"Error loading notification providers: {e}")
    
    def start(self):
        """Start the alert manager thread."""
        if self.running:
            return
        
        self.running = True
        self.check_thread = threading.Thread(
            target=self._check_thread,
            name="AlertManager",
            daemon=True
        )
        self.check_thread.start()
        self.logger.info("Alert manager started")
    
    def stop(self):
        """Stop the alert manager thread."""
        self.running = False
        if self.check_thread and self.check_thread.is_alive():
            self.check_thread.join(timeout=10)
        self.logger.info("Alert manager stopped")
    
    def _check_thread(self):
        """Background thread that periodically checks alert rules."""
        while self.running:
            try:
                self.check_rules()
            except Exception as e:
                self.logger.error(f"Error checking alert rules: {e}", exc_info=True)
            
            # Check for alerts that should be auto-resolved
            self._check_auto_resolve()
            
            # Send notifications for active alerts
            self._send_notifications()
            
            # Sleep until next check
            time.sleep(1)
    
    def add_alert(self, alert: Alert):
        """
        Add an alert to the manager.
        
        Args:
            alert: Alert to add
        """
        self.alerts[alert.name] = alert
        self.logger.info(f"Added alert: {alert.name}")
    
    def add_rule(self, rule: Union[AlertRule, MetricAlertRule]):
        """
        Add a rule to the manager.
        
        Args:
            rule: Rule to add
        """
        if isinstance(rule, MetricAlertRule):
            rule = rule.rule
        
        self.rules[rule.name] = rule
        
        # Make sure the alert is registered
        if rule.alert.name not in self.alerts:
            self.alerts[rule.alert.name] = rule.alert
        
        self.logger.info(f"Added rule: {rule.name}")
    
    def add_metric_rule(
        self,
        name: str,
        metric_name: str,
        threshold: float,
        operator: str = '>',
        description: str = None,
        duration: int = 0,
        severity: AlertSeverity = AlertSeverity.WARNING,
        category: str = "metrics"
    ) -> MetricAlertRule:
        """
        Add a metric-based alert rule.
        
        Args:
            name: Rule name
            metric_name: Name of the metric to monitor
            threshold: Threshold value to compare against
            operator: Comparison operator ('>', '>=', '<', '<=', '==', '!=')
            description: Rule description
            duration: How long the condition must be true (in seconds)
            severity: Alert severity
            category: Alert category
            
        Returns:
            Created MetricAlertRule
        """
        # Create a description if not provided
        if description is None:
            description = f"Alert when {metric_name} {operator} {threshold}"
        
        # Create the rule
        rule = MetricAlertRule(
            name=name,
            description=description,
            metric_name=metric_name,
            threshold=threshold,
            operator=operator,
            duration=duration,
            severity=severity,
            category=category
        )
        
        # Add the rule
        self.add_rule(rule)
        
        return rule
    
    def remove_alert(self, name: str) -> bool:
        """
        Remove an alert from the manager.
        
        Args:
            name: Name of the alert to remove
            
        Returns:
            True if the alert was removed, False otherwise
        """
        if name in self.alerts:
            del self.alerts[name]
            self.logger.info(f"Removed alert: {name}")
            return True
        return False
    
    def remove_rule(self, name: str) -> bool:
        """
        Remove a rule from the manager.
        
        Args:
            name: Name of the rule to remove
            
        Returns:
            True if the rule was removed, False otherwise
        """
        if name in self.rules:
            del self.rules[name]
            self.logger.info(f"Removed rule: {name}")
            return True
        return False
    
    def get_alert(self, name: str) -> Optional[Alert]:
        """
        Get an alert by name.
        
        Args:
            name: Alert name
            
        Returns:
            Alert instance or None if not found
        """
        return self.alerts.get(name)
    
    def get_rule(self, name: str) -> Optional[AlertRule]:
        """
        Get a rule by name.
        
        Args:
            name: Rule name
            
        Returns:
            Rule instance or None if not found
        """
        return self.rules.get(name)
    
    def get_active_alerts(self) -> List[Alert]:
        """
        Get all active alerts.
        
        Returns:
            List of active alerts
        """
        return [
            alert for alert in self.alerts.values()
            if alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]
        ]
    
    def check_rules(self):
        """Check all alert rules."""
        for rule in self.rules.values():
            try:
                rule.check()
            except Exception as e:
                self.logger.error(f"Error checking rule {rule.name}: {e}", exc_info=True)
    
    def _check_auto_resolve(self):
        """Check for alerts that should be auto-resolved."""
        for alert in self.alerts.values():
            if alert.should_auto_resolve():
                alert.resolve()
                self.logger.info(f"Auto-resolved alert: {alert.name}")
                
                # Add to history
                self.alert_history.append({
                    'action': 'auto_resolve',
                    'alert': alert.name,
                    'timestamp': time.time(),
                    'details': {
                        'severity': alert.severity.value,
                        'category': alert.category,
                        'triggered_at': alert.triggered_at,
                        'resolved_at': alert.resolved_at
                    }
                })
    
    def _send_notifications(self):
        """Send notifications for active alerts."""
        for alert in self.alerts.values():
            if alert.should_notify():
                # Update last notification time
                alert.last_notification = time.time()
                
                # Send the notification
                self._send_alert_notification(alert)
    
    def _send_alert_notification(self, alert: Alert):
        """
        Send a notification for an alert.
        
        Args:
            alert: Alert to send notification for
        """
        # Choose the appropriate provider based on severity
        provider_name = 'default'
        if alert.severity == AlertSeverity.CRITICAL and 'slack' in self.notification_providers:
            provider_name = 'slack'
        elif alert.severity == AlertSeverity.ERROR and 'email' in self.notification_providers:
            provider_name = 'email'
        
        provider = self.notification_providers.get(provider_name)
        if not provider:
            self.logger.error(f"No notification provider found for {provider_name}")
            return
        
        # Create the notification message
        title = f"Alert: {alert.name}"
        message = f"{alert.description}\n\nStatus: {alert.status.value}\nSeverity: {alert.severity.value}\nCategory: {alert.category}\n"
        
        if alert.triggered_at:
            message += f"Triggered at: {datetime.fromtimestamp(alert.triggered_at).isoformat()}\n"
        
        if alert.acknowledged_at:
            message += f"Acknowledged at: {datetime.fromtimestamp(alert.acknowledged_at).isoformat()}"
            if alert.acknowledged_by:
                message += f" by {alert.acknowledged_by}"
            message += "\n"
        
        if alert.details:
            message += "\nDetails:\n"
            for key, value in alert.details.items():
                message += f"{key}: {value}\n"
        
        # Send the notification
        try:
            provider.send_notification(
                message=message,
                title=title,
                level=alert.severity.value
            )
            
            self.logger.info(f"Sent notification for alert: {alert.name}")
            
            # Add to history
            self.alert_history.append({
                'action': 'notify',
                'alert': alert.name,
                'timestamp': time.time(),
                'details': {
                    'provider': provider_name,
                    'severity': alert.severity.value,
                    'status': alert.status.value
                }
            })
        
        except Exception as e:
            self.logger.error(f"Error sending notification for alert {alert.name}: {e}", exc_info=True)
    
    def trigger_alert(
        self,
        name: str,
        description: Optional[str] = None,
        severity: AlertSeverity = AlertSeverity.WARNING,
        category: str = "general",
        details: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        Manually trigger an alert.
        
        Args:
            name: Alert name
            description: Alert description (used if creating a new alert)
            severity: Alert severity
            category: Alert category
            details: Additional details about the alert
            
        Returns:
            Triggered alert
        """
        # Get or create the alert
        alert = self.alerts.get(name)
        if not alert:
            if not description:
                description = name
            
            alert = Alert(
                name=name,
                description=description,
                severity=severity,
                category=category
            )
            self.alerts[name] = alert
        
        # Trigger the alert
        alert.trigger(details)
        
        # Add to history
        self.alert_history.append({
            'action': 'trigger',
            'alert': alert.name,
            'timestamp': time.time(),
            'details': {
                'severity': alert.severity.value,
                'category': alert.category,
                'manual': True
            }
        })
        
        self.logger.info(f"Manually triggered alert: {name}")
        
        return alert
    
    def acknowledge_alert(
        self,
        name: str,
        user: Optional[str] = None
    ) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            name: Alert name
            user: User who acknowledged the alert
            
        Returns:
            True if the alert was acknowledged, False otherwise
        """
        alert = self.alerts.get(name)
        if not alert:
            return False
        
        result = alert.acknowledge(user)
        
        if result:
            # Add to history
            self.alert_history.append({
                'action': 'acknowledge',
                'alert': alert.name,
                'timestamp': time.time(),
                'details': {
                    'user': user
                }
            })
            
            self.logger.info(f"Acknowledged alert: {name}")
        
        return result
    
    def resolve_alert(self, name: str) -> bool:
        """
        Resolve an alert.
        
        Args:
            name: Alert name
            
        Returns:
            True if the alert was resolved, False otherwise
        """
        alert = self.alerts.get(name)
        if not alert:
            return False
        
        result = alert.resolve()
        
        if result:
            # Add to history
            self.alert_history.append({
                'action': 'resolve',
                'alert': alert.name,
                'timestamp': time.time(),
                'details': {
                    'manual': True
                }
            })
            
            self.logger.info(f"Resolved alert: {name}")
        
        return result
    
    def silence_alert(self, name: str, silence: bool = True) -> bool:
        """
        Silence or unsilence an alert.
        
        Args:
            name: Alert name
            silence: Whether to silence the alert
            
        Returns:
            True if the alert was silenced, False otherwise
        """
        alert = self.alerts.get(name)
        if not alert:
            return False
        
        alert.silenced = silence
        
        # Add to history
        self.alert_history.append({
            'action': 'silence' if silence else 'unsilence',
            'alert': alert.name,
            'timestamp': time.time()
        })
        
        self.logger.info(f"{'Silenced' if silence else 'Unsilenced'} alert: {name}")
        
        return True
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get the alert history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of alert history entries
        """
        return sorted(
            self.alert_history[-limit:],
            key=lambda x: x['timestamp'],
            reverse=True
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the alert manager status.
        
        Returns:
            Dictionary with alert manager status
        """
        active_alerts = self.get_active_alerts()
        
        return {
            'active_alerts': len(active_alerts),
            'total_alerts': len(self.alerts),
            'total_rules': len(self.rules),
            'notification_providers': list(self.notification_providers.keys()),
            'severity_counts': {
                severity.value: len([a for a in active_alerts if a.severity == severity])
                for severity in AlertSeverity
            }
        }
    
    def save_state(self, filename: str = 'data/alerts/alert_state.json'):
        """
        Save the alert manager state to a file.
        
        Args:
            filename: Filename to save state to
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        state = {
            'alerts': {name: alert.to_dict() for name, alert in self.alerts.items()},
            'rules': {name: rule.to_dict() for name, rule in self.rules.items()},
            'history': self.alert_history
        }
        
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        self.logger.info(f"Saved alert manager state to {filename}")


# Singleton instance
_alert_manager = None

def get_alert_manager():
    """
    Get the singleton alert manager instance.
    
    Returns:
        AlertManager instance
    """
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def start_alerting():
    """Start the alert manager."""
    manager = get_alert_manager()
    manager.start()


def stop_alerting():
    """Stop the alert manager."""
    manager = get_alert_manager()
    manager.stop()


def trigger_alert(
    name: str,
    description: Optional[str] = None,
    severity: AlertSeverity = AlertSeverity.WARNING,
    category: str = "general",
    details: Optional[Dict[str, Any]] = None
) -> Alert:
    """
    Manually trigger an alert.
    
    Args:
        name: Alert name
        description: Alert description (used if creating a new alert)
        severity: Alert severity
        category: Alert category
        details: Additional details about the alert
        
    Returns:
        Triggered alert
    """
    manager = get_alert_manager()
    return manager.trigger_alert(name, description, severity, category, details)


# Create standard system alert rules
def create_standard_rules():
    """Create standard system alert rules."""
    manager = get_alert_manager()
    
    # CPU usage alert
    manager.add_metric_rule(
        name="high_cpu_usage",
        description="High CPU usage detected",
        metric_name="system.cpu_percent",
        threshold=90,
        operator=">",
        duration=300,  # 5 minutes
        severity=AlertSeverity.WARNING,
        category="system"
    )
    
    # Memory usage alert
    manager.add_metric_rule(
        name="high_memory_usage",
        description="High memory usage detected",
        metric_name="system.memory_percent",
        threshold=90,
        operator=">",
        duration=300,  # 5 minutes
        severity=AlertSeverity.WARNING,
        category="system"
    )
    
    # Disk usage alert
    manager.add_metric_rule(
        name="high_disk_usage",
        description="High disk usage detected",
        metric_name="system.disk_root_percent",
        threshold=90,
        operator=">",
        duration=0,  # Immediate
        severity=AlertSeverity.WARNING,
        category="system"
    )
    
    # Error rate alert
    manager.add_metric_rule(
        name="high_error_rate",
        description="High error rate detected",
        metric_name="log_levels.ERROR",
        threshold=10,
        operator=">",
        duration=60,  # 1 minute
        severity=AlertSeverity.ERROR,
        category="logs"
    )
    
    # Task failure alert
    manager.add_metric_rule(
        name="task_failures",
        description="Multiple task failures detected",
        metric_name="tasks.failed",
        threshold=3,
        operator=">=",
        duration=300,  # 5 minutes
        severity=AlertSeverity.ERROR,
        category="tasks"
    )
    
    # API latency alert
    manager.add_metric_rule(
        name="high_api_latency",
        description="High API response time detected",
        metric_name="api.response_time",
        threshold=2000,  # 2 seconds
        operator=">",
        duration=300,  # 5 minutes
        severity=AlertSeverity.WARNING,
        category="api"
    )