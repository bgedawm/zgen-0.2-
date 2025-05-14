"""
Task Scheduler Triggers Module
---------------------------
This module provides trigger definitions for the task scheduler.
"""

import os
import logging
import re
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from utils.logger import get_logger


class TriggerParser:
    """Parses schedule specifications into APScheduler triggers."""
    
    def __init__(self):
        """Initialize the trigger parser."""
        self.logger = get_logger(__name__)
    
    def parse(self, schedule_spec: str, start_time: Optional[datetime] = None) -> Optional[Union[CronTrigger, IntervalTrigger, DateTrigger]]:
        """
        Parse a schedule specification into a trigger.
        
        Args:
            schedule_spec: The schedule specification
            start_time: Optional start time
            
        Returns:
            A trigger object or None if invalid
        """
        try:
            # Check for cron schedule (starts with "cron:")
            if schedule_spec.startswith("cron:"):
                return self._parse_cron(schedule_spec)
            
            # Check for interval schedule (e.g., "every 1h", "every 30m", "every 1d")
            elif schedule_spec.startswith("every "):
                return self._parse_interval(schedule_spec, start_time)
            
            # Check for date schedule (ISO format)
            elif schedule_spec.startswith("at:"):
                return self._parse_date(schedule_spec)
            
            # Check for relative date (e.g., "in 1h", "in 30m", "in 1d")
            elif schedule_spec.startswith("in "):
                return self._parse_relative(schedule_spec)
            
            else:
                self.logger.error(f"Unknown schedule format: {schedule_spec}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error parsing schedule {schedule_spec}: {str(e)}")
            return None
    
    def _parse_cron(self, schedule_spec: str) -> Optional[CronTrigger]:
        """
        Parse a cron schedule specification.
        
        Args:
            schedule_spec: The cron schedule specification
            
        Returns:
            A CronTrigger object or None if invalid
        """
        cron_expr = schedule_spec[5:].strip()
        
        # Validate cron expression
        if not self._validate_cron(cron_expr):
            self.logger.error(f"Invalid cron expression: {cron_expr}")
            return None
        
        try:
            return CronTrigger.from_crontab(cron_expr)
        except Exception as e:
            self.logger.error(f"Error creating CronTrigger: {str(e)}")
            return None
    
    def _validate_cron(self, cron_expr: str) -> bool:
        """
        Validate a cron expression.
        
        Args:
            cron_expr: The cron expression
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation
        parts = cron_expr.split()
        if len(parts) != 5:
            return False
        
        # Validate each field
        patterns = [
            r'^(\*|(?:[0-5]?\d)(?:-(?:[0-5]?\d))?(?:,(?:[0-5]?\d)(?:-(?:[0-5]?\d))?)*|\*/\d+)$',  # minute
            r'^(\*|(?:1?\d|2[0-3])(?:-(?:1?\d|2[0-3]))?(?:,(?:1?\d|2[0-3])(?:-(?:1?\d|2[0-3]))?)*|\*/\d+)$',  # hour
            r'^(\*|(?:[1-9]|[12]\d|3[01])(?:-(?:[1-9]|[12]\d|3[01]))?(?:,(?:[1-9]|[12]\d|3[01])(?:-(?:[1-9]|[12]\d|3[01]))?)*|\*/\d+)$',  # day of month
            r'^(\*|(?:[1-9]|1[0-2])(?:-(?:[1-9]|1[0-2]))?(?:,(?:[1-9]|1[0-2])(?:-(?:[1-9]|1[0-2]))?)*|\*/\d+)$',  # month
            r'^(\*|[0-6](?:-[0-6])?(?:,[0-6](?:-[0-6])?)*|\*/\d+)$'  # day of week
        ]
        
        for i, pattern in enumerate(patterns):
            if not re.match(pattern, parts[i]):
                return False
        
        return True
    
    def _parse_interval(self, schedule_spec: str, start_time: Optional[datetime] = None) -> Optional[IntervalTrigger]:
        """
        Parse an interval schedule specification.
        
        Args:
            schedule_spec: The interval schedule specification
            start_time: Optional start time
            
        Returns:
            An IntervalTrigger object or None if invalid
        """
        interval_spec = schedule_spec[6:].strip()
        
        # Match the pattern: {number}{unit}
        match = re.match(r'^(\d+)([smhd])$', interval_spec)
        if not match:
            self.logger.error(f"Invalid interval specification: {interval_spec}")
            return None
        
        value = int(match.group(1))
        unit = match.group(2)
        
        if value <= 0:
            self.logger.error(f"Interval value must be positive: {value}")
            return None
        
        try:
            kwargs = {"start_date": start_time}
            
            if unit == 's':
                kwargs["seconds"] = value
            elif unit == 'm':
                kwargs["minutes"] = value
            elif unit == 'h':
                kwargs["hours"] = value
            elif unit == 'd':
                kwargs["days"] = value
            
            return IntervalTrigger(**kwargs)
        except Exception as e:
            self.logger.error(f"Error creating IntervalTrigger: {str(e)}")
            return None
    
    def _parse_date(self, schedule_spec: str) -> Optional[DateTrigger]:
        """
        Parse a date schedule specification.
        
        Args:
            schedule_spec: The date schedule specification
            
        Returns:
            A DateTrigger object or None if invalid
        """
        date_str = schedule_spec[3:].strip()
        
        try:
            run_date = datetime.fromisoformat(date_str)
            
            # Ensure the date is in the future
            if run_date <= datetime.now():
                self.logger.warning(f"Date is in the past: {date_str}")
            
            return DateTrigger(run_date=run_date)
        except Exception as e:
            self.logger.error(f"Error parsing date {date_str}: {str(e)}")
            return None
    
    def _parse_relative(self, schedule_spec: str) -> Optional[DateTrigger]:
        """
        Parse a relative date schedule specification.
        
        Args:
            schedule_spec: The relative date schedule specification
            
        Returns:
            A DateTrigger object or None if invalid
        """
        relative_spec = schedule_spec[3:].strip()
        
        # Match the pattern: {number}{unit}
        match = re.match(r'^(\d+)([smhd])$', relative_spec)
        if not match:
            self.logger.error(f"Invalid relative specification: {relative_spec}")
            return None
        
        value = int(match.group(1))
        unit = match.group(2)
        
        if value <= 0:
            self.logger.error(f"Relative value must be positive: {value}")
            return None
        
        try:
            now = datetime.now()
            
            if unit == 's':
                run_date = now + timedelta(seconds=value)
            elif unit == 'm':
                run_date = now + timedelta(minutes=value)
            elif unit == 'h':
                run_date = now + timedelta(hours=value)
            elif unit == 'd':
                run_date = now + timedelta(days=value)
            else:
                return None
            
            return DateTrigger(run_date=run_date)
        except Exception as e:
            self.logger.error(f"Error creating DateTrigger: {str(e)}")
            return None
    
    def get_trigger_info(self, trigger: Union[CronTrigger, IntervalTrigger, DateTrigger]) -> Dict[str, Any]:
        """
        Get information about a trigger.
        
        Args:
            trigger: The trigger object
            
        Returns:
            A dictionary with trigger information
        """
        trigger_info = {}
        
        if isinstance(trigger, CronTrigger):
            trigger_info["type"] = "cron"
            for field in trigger.fields:
                trigger_info[field.name] = str(field)
        elif isinstance(trigger, IntervalTrigger):
            trigger_info["type"] = "interval"
            trigger_info["seconds"] = trigger.interval.total_seconds()
        elif isinstance(trigger, DateTrigger):
            trigger_info["type"] = "date"
            trigger_info["run_date"] = trigger.run_date.isoformat()
        
        return trigger_info
    
    def get_human_readable(self, schedule_spec: str) -> str:
        """
        Get a human-readable description of a schedule specification.
        
        Args:
            schedule_spec: The schedule specification
            
        Returns:
            A human-readable description
        """
        try:
            if schedule_spec.startswith("cron:"):
                cron_expr = schedule_spec[5:].strip()
                return f"Cron schedule: {cron_expr}"
            
            elif schedule_spec.startswith("every "):
                interval_spec = schedule_spec[6:].strip()
                
                # Match the pattern: {number}{unit}
                match = re.match(r'^(\d+)([smhd])$', interval_spec)
                if not match:
                    return schedule_spec
                
                value = int(match.group(1))
                unit = match.group(2)
                
                unit_names = {
                    's': 'second' if value == 1 else 'seconds',
                    'm': 'minute' if value == 1 else 'minutes',
                    'h': 'hour' if value == 1 else 'hours',
                    'd': 'day' if value == 1 else 'days'
                }
                
                return f"Every {value} {unit_names[unit]}"
            
            elif schedule_spec.startswith("at:"):
                date_str = schedule_spec[3:].strip()
                try:
                    run_date = datetime.fromisoformat(date_str)
                    return f"At {run_date.strftime('%Y-%m-%d %H:%M:%S')}"
                except:
                    return f"At {date_str}"
            
            elif schedule_spec.startswith("in "):
                relative_spec = schedule_spec[3:].strip()
                
                # Match the pattern: {number}{unit}
                match = re.match(r'^(\d+)([smhd])$', relative_spec)
                if not match:
                    return schedule_spec
                
                value = int(match.group(1))
                unit = match.group(2)
                
                unit_names = {
                    's': 'second' if value == 1 else 'seconds',
                    'm': 'minute' if value == 1 else 'minutes',
                    'h': 'hour' if value == 1 else 'hours',
                    'd': 'day' if value == 1 else 'days'
                }
                
                return f"In {value} {unit_names[unit]}"
            
            else:
                return schedule_spec
        
        except Exception as e:
            self.logger.error(f"Error getting human-readable description: {str(e)}")
            return schedule_spec