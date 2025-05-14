"""
Task Scheduler Module
------------------
This module provides task scheduling capabilities for the agent.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Union, Callable
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError

from utils.logger import get_logger
from scheduler.persistence import SchedulerPersistence
from scheduler.triggers import TriggerParser


class TaskScheduler:
    """Provides task scheduling capabilities for the agent."""
    
    def __init__(self, agent, persistence_path: Optional[str] = None):
        """
        Initialize the task scheduler.
        
        Args:
            agent: The Scout agent
            persistence_path: The path to store scheduler data
        """
        self.logger = get_logger(__name__)
        self.agent = agent
        
        # Set persistence path
        if persistence_path is None:
            persistence_path = os.getenv("SCHEDULER_PERSISTENCE_PATH", "./data/scheduler")
        
        # Initialize persistence
        self.persistence = SchedulerPersistence(persistence_path)
        
        # Initialize trigger parser
        self.trigger_parser = TriggerParser()
        
        # Initialize the scheduler
        self.scheduler = AsyncIOScheduler()
        
        # Configure scheduler
        self._configure_scheduler()
        
        # Track scheduled jobs by task ID
        self.scheduled_tasks: Dict[str, str] = {}  # task_id -> job_id
        
        # Track running tasks
        self.running_tasks: Set[str] = set()
        
        # Track listeners
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []
        
        self.logger.info("Task scheduler initialized")
    
    def _configure_scheduler(self):
        """Configure the scheduler."""
        # Set timezone
        timezone = os.getenv("SCHEDULER_TIMEZONE", "UTC")
        
        # Set max instances
        max_instances = int(os.getenv("SCHEDULER_MAX_INSTANCES", "3"))
        
        # Set misc options
        self.scheduler.configure(
            timezone=timezone,
            job_defaults={
                'coalesce': True,
                'max_instances': max_instances,
                'misfire_grace_time': 60
            }
        )
    
    def start(self):
        """Start the scheduler."""
        # Load persisted schedules
        self._load_schedules()
        
        # Start the scheduler
        self.scheduler.start()
        
        # Schedule cleanup task
        self._schedule_cleanup()
        
        self.logger.info("Task scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        # Shutdown the scheduler
        self.scheduler.shutdown()
        self.logger.info("Task scheduler shutdown")
    
    def schedule_task(self, task_id: str, schedule_spec: str, start_time: Optional[datetime] = None) -> bool:
        """
        Schedule a task for execution.
        
        Args:
            task_id: The task ID
            schedule_spec: The schedule specification (cron expression, interval, or date)
            start_time: Optional start time for the schedule
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if the task exists
            if task_id not in self.agent.tasks:
                self.logger.error(f"Cannot schedule task {task_id}: Task not found")
                return False
            
            # Parse the schedule specification
            trigger = self.trigger_parser.parse(schedule_spec, start_time)
            if trigger is None:
                self.logger.error(f"Invalid schedule specification: {schedule_spec}")
                return False
            
            # Extract schedule type
            if isinstance(trigger, CronTrigger):
                schedule_type = "cron"
            elif isinstance(trigger, IntervalTrigger):
                schedule_type = "interval"
            elif isinstance(trigger, DateTrigger):
                schedule_type = "date"
            else:
                schedule_type = "unknown"
            
            # Add the job to the scheduler
            job = self.scheduler.add_job(
                self._execute_task,
                trigger=trigger,
                args=[task_id],
                id=f"task_{task_id}_{datetime.now().timestamp()}",
                replace_existing=True
            )
            
            # Track the job
            self.scheduled_tasks[task_id] = job.id
            
            # Get human-readable description
            human_readable = self.trigger_parser.get_human_readable(schedule_spec)
            
            # Persist the schedule
            self.persistence.save_schedule(
                task_id=task_id,
                job_id=job.id,
                schedule_type=schedule_type,
                schedule_value=schedule_spec,
                next_run_time=job.next_run_time
            )
            
            # Update task with schedule info
            task = self.agent.tasks[task_id]
            task.schedule = human_readable
            task.next_run_time = job.next_run_time
            
            # Notify listeners
            self._notify_listeners({
                "type": "schedule_update",
                "task_id": task_id,
                "schedule": {
                    "job_id": job.id,
                    "schedule_type": schedule_type,
                    "schedule_value": schedule_spec,
                    "human_readable": human_readable,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                }
            })
            
            self.logger.info(f"Scheduled task {task_id} with schedule: {schedule_spec}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error scheduling task {task_id}: {str(e)}")
            return False
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if task_id not in self.scheduled_tasks:
                self.logger.warning(f"Cannot cancel task {task_id}: Not scheduled")
                return False
            
            job_id = self.scheduled_tasks[task_id]
            
            try:
                self.scheduler.remove_job(job_id)
            except JobLookupError:
                self.logger.warning(f"Job {job_id} not found in scheduler")
            
            # Remove from tracking
            del self.scheduled_tasks[task_id]
            
            # Remove from persistence
            self.persistence.delete_schedule(task_id)
            
            # Update task
            if task_id in self.agent.tasks:
                task = self.agent.tasks[task_id]
                task.schedule = None
                task.next_run_time = None
            
            # Notify listeners
            self._notify_listeners({
                "type": "schedule_removed",
                "task_id": task_id
            })
            
            self.logger.info(f"Cancelled scheduled task {task_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error cancelling task {task_id}: {str(e)}")
            return False
    
    def get_task_schedule(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the schedule for a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The schedule information or None if not scheduled
        """
        if task_id not in self.scheduled_tasks:
            return None
        
        job_id = self.scheduled_tasks[task_id]
        
        try:
            job = self.scheduler.get_job(job_id)
            if job is None:
                return None
            
            # Get schedule from persistence
            schedule = self.persistence.get_schedule(task_id)
            if not schedule:
                return None
            
            # Extract trigger information
            trigger_info = self.trigger_parser.get_trigger_info(job.trigger)
            
            # Get human-readable description
            human_readable = self.trigger_parser.get_human_readable(schedule["schedule_value"])
            
            return {
                "task_id": task_id,
                "job_id": job_id,
                "schedule_type": schedule["schedule_type"],
                "schedule_value": schedule["schedule_value"],
                "human_readable": human_readable,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": trigger_info
            }
        
        except Exception as e:
            self.logger.error(f"Error getting schedule for task {task_id}: {str(e)}")
            return None
    
    def get_all_schedules(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all scheduled tasks.
        
        Returns:
            A dictionary of task schedules
        """
        schedules = {}
        
        for task_id, job_id in self.scheduled_tasks.items():
            schedule = self.get_task_schedule(task_id)
            if schedule:
                schedules[task_id] = schedule
        
        return schedules
    
    def get_task_runs(self, task_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the execution history for a task.
        
        Args:
            task_id: The task ID
            limit: Maximum number of runs to return
            
        Returns:
            A list of task runs
        """
        return self.persistence.get_task_runs(task_id, limit)
    
    def add_listener(self, listener: Callable[[Dict[str, Any]], None]):
        """
        Add a listener for task events.
        
        Args:
            listener: The listener function
        """
        self.listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[Dict[str, Any]], None]):
        """
        Remove a listener.
        
        Args:
            listener: The listener function
        """
        if listener in self.listeners:
            self.listeners.remove(listener)
    
    async def _execute_task(self, task_id: str):
        """
        Execute a scheduled task.
        
        Args:
            task_id: The task ID
        """
        try:
            # Check if the task exists
            if task_id not in self.agent.tasks:
                self.logger.error(f"Cannot execute task {task_id}: Task not found")
                return
            
            # Check if the task is already running
            if task_id in self.running_tasks:
                self.logger.warning(f"Task {task_id} is already running, skipping execution")
                return
            
            # Mark as running
            self.running_tasks.add(task_id)
            start_time = datetime.now()
            
            # Log task run start
            self.persistence.log_task_run(
                task_id=task_id,
                status="running",
                start_time=start_time
            )
            
            # Notify listeners
            self._notify_listeners({
                "type": "task_started",
                "task_id": task_id,
                "start_time": start_time.isoformat()
            })
            
            # Get the task
            task = self.agent.tasks[task_id]
            
            # Reset task status
            task.status = "pending"
            task.progress = 0
            task.result = None
            task.error = None
            task.updated_at = datetime.now()
            
            # Execute the task
            await self.agent._execute_task(task, "scheduler")
            
            # Log task run end
            end_time = datetime.now()
            self.persistence.log_task_run(
                task_id=task_id,
                status=task.status,
                start_time=start_time,
                end_time=end_time,
                error=task.error
            )
            
            # Notify listeners
            self._notify_listeners({
                "type": "task_finished",
                "task_id": task_id,
                "status": task.status,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "error": task.error
            })
            
            # Mark as not running
            self.running_tasks.remove(task_id)
        
        except Exception as e:
            self.logger.error(f"Error executing scheduled task {task_id}: {str(e)}")
            
            # Log task run end with error
            end_time = datetime.now()
            self.persistence.log_task_run(
                task_id=task_id,
                status="failed",
                start_time=start_time if 'start_time' in locals() else datetime.now(),
                end_time=end_time,
                error=str(e)
            )
            
            # Notify listeners
            self._notify_listeners({
                "type": "task_error",
                "task_id": task_id,
                "error": str(e),
                "end_time": end_time.isoformat()
            })
            
            # Mark as not running
            if task_id in self.running_tasks:
                self.running_tasks.remove(task_id)
    
    def _load_schedules(self):
        """Load schedules from persistence."""
        try:
            schedules = self.persistence.get_all_schedules()
            
            loaded_count = 0
            
            for schedule in schedules:
                task_id = schedule["task_id"]
                
                # Check if the task exists
                if task_id not in self.agent.tasks:
                    self.logger.warning(f"Cannot load schedule for task {task_id}: Task not found")
                    continue
                
                schedule_type = schedule["schedule_type"]
                schedule_value = schedule["schedule_value"]
                
                # Skip schedules that are in the past
                if schedule_type == "date":
                    try:
                        date_str = schedule_value.split(":", 1)[1].strip()
                        run_date = datetime.fromisoformat(date_str)
                        if run_date <= datetime.now():
                            self.logger.warning(f"Skipping past date schedule for task {task_id}")
                            continue
                    except:
                        pass
                
                # Schedule the task
                success = self.schedule_task(task_id, schedule_value)
                if success:
                    loaded_count += 1
            
            self.logger.info(f"Loaded {loaded_count} schedules")
        
        except Exception as e:
            self.logger.error(f"Error loading schedules: {str(e)}")
    
    def _notify_listeners(self, event: Dict[str, Any]):
        """
        Notify listeners of an event.
        
        Args:
            event: The event data
        """
        for listener in self.listeners:
            try:
                listener(event)
            except Exception as e:
                self.logger.error(f"Error in listener: {str(e)}")
    
    def _schedule_cleanup(self):
        """Schedule the cleanup task."""
        # Run cleanup once a day
        self.scheduler.add_job(
            self._cleanup_task,
            trigger=CronTrigger(hour=0, minute=0),  # Run at midnight
            id="cleanup_task",
            replace_existing=True
        )
    
    async def _cleanup_task(self):
        """Cleanup old task runs."""
        try:
            # Get retention days from config
            retention_days = int(os.getenv("SCHEDULER_RETENTION_DAYS", "30"))
            
            # Cleanup old task runs
            self.persistence.cleanup_old_runs(retention_days)
            
            self.logger.info(f"Cleaned up old task runs (retention: {retention_days} days)")
        except Exception as e:
            self.logger.error(f"Error in cleanup task: {str(e)}")