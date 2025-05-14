"""
Task API Endpoints
---------------
This module contains all API endpoints related to tasks.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from fastapi.responses import FileResponse

from core.agent import AgentTask

# Setup logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

# This will be initialized when the app is created
agent = None
scheduler = None


def get_agent():
    if agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return agent


def get_scheduler():
    if scheduler is None:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    return scheduler


def task_to_response(task: AgentTask) -> Dict[str, Any]:
    """
    Convert an AgentTask to a response dictionary.
    
    Args:
        task: The agent task
        
    Returns:
        The task response dictionary
    """
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "status": task.status,
        "progress": task.progress,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "result": task.result,
        "error": task.error,
        "artifacts": task.artifacts,
        "schedule": task.schedule,
        "next_run_time": task.next_run_time.isoformat() if task.next_run_time else None
    }


@router.post("/")
async def create_task(
    name: str = Form(...),
    description: str = Form(...),
    schedule: Optional[str] = Form(None),
    files: List[UploadFile] = File([])
):
    """
    Create a new task.
    
    Args:
        name: The task name
        description: The task description
        schedule: Optional schedule specification
        files: Optional files to attach to the task
        
    Returns:
        The created task
    """
    try:
        # Create a task
        task = AgentTask(
            name=name,
            description=description
        )
        
        # Process uploaded files
        if files:
            file_dir = os.path.join("data", "uploads", task.id)
            os.makedirs(file_dir, exist_ok=True)
            
            for file in files:
                file_path = os.path.join(file_dir, file.filename)
                
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                
                task.artifacts.append(file_path)
        
        # Add task to agent
        get_agent().tasks[task.id] = task
        
        # Notify the task listeners
        get_agent()._notify_task_listeners(task)
        
        # Schedule the task if requested
        if schedule:
            get_scheduler().schedule_task(task.id, schedule)
        else:
            # Otherwise, execute it immediately
            await get_agent()._execute_task(task, "api")
        
        return task_to_response(task)
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_tasks():
    """
    Get all tasks.
    
    Returns:
        A list of tasks
    """
    try:
        return [task_to_response(task) for task in get_agent().tasks.values()]
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}")
async def get_task(task_id: str):
    """
    Get a specific task.
    
    Args:
        task_id: The task ID
        
    Returns:
        The task
    """
    try:
        if task_id not in get_agent().tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task_to_response(get_agent().tasks[task_id])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """
    Delete a specific task.
    
    Args:
        task_id: The task ID
        
    Returns:
        A success message
    """
    try:
        if task_id not in get_agent().tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Cancel any scheduled executions
        get_scheduler().cancel_task(task_id)
        
        # Remove the task
        del get_agent().tasks[task_id]
        
        return {"success": True, "message": "Task deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/schedule")
async def schedule_task(task_id: str, schedule: Dict[str, str]):
    """
    Schedule a task.
    
    Args:
        task_id: The task ID
        schedule: The schedule request
        
    Returns:
        The schedule information
    """
    try:
        if task_id not in get_agent().tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        success = get_scheduler().schedule_task(task_id, schedule["schedule"])
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to schedule task")
        
        schedule_info = get_scheduler().get_task_schedule(task_id)
        
        if not schedule_info:
            raise HTTPException(status_code=500, detail="Failed to get schedule information")
        
        return {
            "success": True,
            "schedule": schedule_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}/schedule")
async def cancel_task_schedule(task_id: str):
    """
    Cancel a task schedule.
    
    Args:
        task_id: The task ID
        
    Returns:
        Success status
    """
    try:
        if task_id not in get_agent().tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        success = get_scheduler().cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to cancel schedule")
        
        return {
            "success": True,
            "message": "Schedule cancelled"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/schedule")
async def get_task_schedule(task_id: str):
    """
    Get a task's schedule.
    
    Args:
        task_id: The task ID
        
    Returns:
        The schedule information
    """
    try:
        if task_id not in get_agent().tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        schedule = get_scheduler().get_task_schedule(task_id)
        
        if not schedule:
            return {
                "success": True,
                "has_schedule": False
            }
        
        return {
            "success": True,
            "has_schedule": True,
            "schedule": schedule
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/runs")
async def get_task_runs(task_id: str, limit: int = 10):
    """
    Get a task's execution history.
    
    Args:
        task_id: The task ID
        limit: Maximum number of runs to return
        
    Returns:
        The task runs
    """
    try:
        if task_id not in get_agent().tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        runs = get_scheduler().get_task_runs(task_id, limit)
        
        return {
            "success": True,
            "runs": runs
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task runs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/artifacts/{artifact_index}")
async def get_task_artifact(task_id: str, artifact_index: int):
    """
    Get a specific task artifact.
    
    Args:
        task_id: The task ID
        artifact_index: The artifact index
        
    Returns:
        The artifact file
    """
    try:
        if task_id not in get_agent().tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = get_agent().tasks[task_id]
        
        if artifact_index < 0 or artifact_index >= len(task.artifacts):
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        artifact_path = task.artifacts[artifact_index]
        
        if not os.path.exists(artifact_path):
            raise HTTPException(status_code=404, detail="Artifact file not found")
        
        return FileResponse(artifact_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task artifact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))