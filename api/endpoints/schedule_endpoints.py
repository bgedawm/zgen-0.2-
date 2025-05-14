"""
Schedule API Endpoints
-----------------
This module contains all API endpoints related to scheduling.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

# Setup logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])

# This will be initialized when the app is created
scheduler = None


def get_scheduler():
    if scheduler is None:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    return scheduler


@router.get("/")
async def get_all_schedules():
    """
    Get all scheduled tasks.
    
    Returns:
        A dictionary of schedules
    """
    try:
        schedules = get_scheduler().get_all_schedules()
        
        return {
            "success": True,
            "schedules": schedules
        }
    except Exception as e:
        logger.error(f"Error getting schedules: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str):
    """
    Get a specific schedule.
    
    Args:
        schedule_id: The schedule ID (same as task ID)
        
    Returns:
        The schedule information
    """
    try:
        schedule = get_scheduler().get_task_schedule(schedule_id)
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        return {
            "success": True,
            "schedule": schedule
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upcoming")
async def get_upcoming_schedules(limit: int = 10):
    """
    Get upcoming scheduled tasks.
    
    Args:
        limit: Maximum number of schedules to return
        
    Returns:
        A list of upcoming schedules
    """
    try:
        # Get all schedules
        all_schedules = get_scheduler().get_all_schedules()
        
        # Filter schedules with next_run_time
        upcoming = []
        for task_id, schedule in all_schedules.items():
            if schedule.get("next_run_time"):
                upcoming.append(schedule)
        
        # Sort by next_run_time
        upcoming.sort(key=lambda x: x.get("next_run_time", ""))
        
        # Limit results
        upcoming = upcoming[:limit]
        
        return {
            "success": True,
            "schedules": upcoming
        }
    except Exception as e:
        logger.error(f"Error getting upcoming schedules: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_execution_history(limit: int = 20):
    """
    Get execution history for all scheduled tasks.
    
    Args:
        limit: Maximum number of entries to return
        
    Returns:
        A list of execution history entries
    """
    try:
        # Get all schedules
        all_schedules = get_scheduler().get_all_schedules()
        
        # Get history for each schedule
        history = []
        for task_id in all_schedules.keys():
            task_runs = get_scheduler().get_task_runs(task_id, 5)  # Get last 5 runs per task
            for run in task_runs:
                run["task_id"] = task_id
                history.append(run)
        
        # Sort by start_time
        history.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        
        # Limit results
        history = history[:limit]
        
        return {
            "success": True,
            "history": history
        }
    except Exception as e:
        logger.error(f"Error getting execution history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))