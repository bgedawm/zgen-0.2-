"""
Task Scheduler Persistence Module
-------------------------------
This module provides persistence capabilities for the task scheduler.
"""

import os
import json
import logging
import sqlite3
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger


class SchedulerPersistence:
    """Provides persistence capabilities for the task scheduler."""
    
    def __init__(self, persistence_path: Optional[str] = None):
        """
        Initialize the scheduler persistence.
        
        Args:
            persistence_path: The path to store scheduler data
        """
        self.logger = get_logger(__name__)
        
        # Set persistence path
        if persistence_path is None:
            persistence_path = os.getenv("SCHEDULER_PERSISTENCE_PATH", "./data/scheduler")
        
        self.persistence_path = Path(persistence_path)
        
        # Create persistence directory if it doesn't exist
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        
        # SQLite database file
        self.db_file = self.persistence_path / "scheduler.db"
        
        # Legacy JSON file for backwards compatibility
        self.json_file = self.persistence_path / "scheduled_tasks.json"
        
        # Initialize the database
        self._init_db()
        
        # Migrate from JSON if needed
        self._migrate_from_json()
        
        self.logger.info(f"Scheduler persistence initialized at {self.persistence_path}")
    
    def _init_db(self):
        """Initialize the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Create schedules table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                schedule_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                next_run_time TIMESTAMP,
                UNIQUE(task_id)
            )
            ''')
            
            # Create task_runs table for logging task executions
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                error TEXT
            )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.debug("Database initialized")
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
    
    def _migrate_from_json(self):
        """Migrate schedules from JSON file if it exists."""
        if not self.json_file.exists():
            return
        
        try:
            with open(self.json_file, "r") as f:
                schedules = json.load(f)
            
            if not schedules:
                return
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            for task_id, schedule in schedules.items():
                # Check if already migrated
                cursor.execute("SELECT COUNT(*) FROM schedules WHERE task_id = ?", (task_id,))
                if cursor.fetchone()[0] > 0:
                    continue
                
                trigger = schedule.get("trigger", {})
                schedule_type = trigger.get("type", "unknown")
                
                # Convert trigger to schedule value
                if schedule_type == "cron":
                    cron_parts = []
                    for field in ["minute", "hour", "day", "month", "day_of_week"]:
                        if field in trigger:
                            cron_parts.append(trigger[field])
                    
                    if len(cron_parts) == 5:
                        schedule_value = f"cron:{' '.join(cron_parts)}"
                    else:
                        schedule_value = "unknown"
                
                elif schedule_type == "interval":
                    seconds = trigger.get("seconds", 0)
                    if seconds > 0:
                        if seconds < 60:
                            schedule_value = f"every {seconds}s"
                        elif seconds < 3600:
                            minutes = seconds // 60
                            schedule_value = f"every {minutes}m"
                        elif seconds < 86400:
                            hours = seconds // 3600
                            schedule_value = f"every {hours}h"
                        else:
                            days = seconds // 86400
                            schedule_value = f"every {days}d"
                    else:
                        schedule_value = "unknown"
                
                elif schedule_type == "date":
                    run_date = trigger.get("run_date")
                    if run_date:
                        schedule_value = f"at:{run_date}"
                    else:
                        schedule_value = "unknown"
                
                else:
                    schedule_value = "unknown"
                
                # Insert into database
                cursor.execute(
                    "INSERT INTO schedules (task_id, job_id, schedule_type, schedule_value, next_run_time) VALUES (?, ?, ?, ?, ?)",
                    (
                        task_id,
                        schedule.get("job_id", ""),
                        schedule_type,
                        schedule_value,
                        schedule.get("next_run_time")
                    )
                )
            
            conn.commit()
            conn.close()
            
            # Rename the JSON file to indicate it was migrated
            self.json_file.rename(self.json_file.with_suffix(".json.migrated"))
            
            self.logger.info("Migrated schedules from JSON to SQLite")
        except Exception as e:
            self.logger.error(f"Error migrating from JSON: {str(e)}")
    
    def save_schedule(self, task_id: str, job_id: str, schedule_type: str, schedule_value: str, next_run_time: Optional[datetime] = None):
        """
        Save a schedule to the database.
        
        Args:
            task_id: The task ID
            job_id: The job ID
            schedule_type: The schedule type (cron, interval, date)
            schedule_value: The schedule value
            next_run_time: The next run time
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Convert datetime to string
            next_run_time_str = next_run_time.isoformat() if next_run_time else None
            
            # Check if the schedule already exists
            cursor.execute("SELECT COUNT(*) FROM schedules WHERE task_id = ?", (task_id,))
            if cursor.fetchone()[0] > 0:
                # Update the existing schedule
                cursor.execute(
                    "UPDATE schedules SET job_id = ?, schedule_type = ?, schedule_value = ?, next_run_time = ? WHERE task_id = ?",
                    (job_id, schedule_type, schedule_value, next_run_time_str, task_id)
                )
            else:
                # Insert a new schedule
                cursor.execute(
                    "INSERT INTO schedules (task_id, job_id, schedule_type, schedule_value, next_run_time) VALUES (?, ?, ?, ?, ?)",
                    (task_id, job_id, schedule_type, schedule_value, next_run_time_str)
                )
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Saved schedule for task {task_id}")
        except Exception as e:
            self.logger.error(f"Error saving schedule for task {task_id}: {str(e)}")
    
    def delete_schedule(self, task_id: str):
        """
        Delete a schedule from the database.
        
        Args:
            task_id: The task ID
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM schedules WHERE task_id = ?", (task_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Deleted schedule for task {task_id}")
        except Exception as e:
            self.logger.error(f"Error deleting schedule for task {task_id}: {str(e)}")
    
    def get_schedule(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a schedule from the database.
        
        Args:
            task_id: The task ID
            
        Returns:
            The schedule or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM schedules WHERE task_id = ?",
                (task_id,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            else:
                return None
        except Exception as e:
            self.logger.error(f"Error getting schedule for task {task_id}: {str(e)}")
            return None
    
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """
        Get all schedules from the database.
        
        Returns:
            A list of schedules
        """
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM schedules")
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting all schedules: {str(e)}")
            return []
    
    def log_task_run(self, task_id: str, status: str, start_time: datetime, end_time: Optional[datetime] = None, error: Optional[str] = None):
        """
        Log a task run to the database.
        
        Args:
            task_id: The task ID
            status: The run status
            start_time: The start time
            end_time: The end time
            error: Any error message
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Convert datetimes to strings
            start_time_str = start_time.isoformat() if start_time else None
            end_time_str = end_time.isoformat() if end_time else None
            
            cursor.execute(
                "INSERT INTO task_runs (task_id, status, start_time, end_time, error) VALUES (?, ?, ?, ?, ?)",
                (task_id, status, start_time_str, end_time_str, error)
            )
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Logged task run for task {task_id}")
        except Exception as e:
            self.logger.error(f"Error logging task run for task {task_id}: {str(e)}")
    
    def get_task_runs(self, task_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get task runs for a specific task.
        
        Args:
            task_id: The task ID
            limit: Maximum number of runs to return
            
        Returns:
            A list of task runs
        """
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM task_runs WHERE task_id = ? ORDER BY start_time DESC LIMIT ?",
                (task_id, limit)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting task runs for task {task_id}: {str(e)}")
            return []
    
    def cleanup_old_runs(self, days: int = 30):
        """
        Clean up old task runs.
        
        Args:
            days: Number of days to keep
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Delete runs older than the specified number of days
            cursor.execute(
                "DELETE FROM task_runs WHERE start_time < datetime('now', ?)",
                (f"-{days} days",)
            )
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old task runs")
        except Exception as e:
            self.logger.error(f"Error cleaning up old task runs: {str(e)}")