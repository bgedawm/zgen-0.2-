"""
API Application Module
-------------------
This module provides the FastAPI application for the agent.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from core.agent import ScoutAgent, AgentTask, AgentResponse
from scheduler.scheduler import TaskScheduler
from utils.logger import get_logger


# API models for requests and responses
class ProcessInputRequest(BaseModel):
    """Request model for processing input."""
    input: str
    session_id: Optional[str] = "default"


class TaskRequest(BaseModel):
    """Request model for creating a task."""
    name: str
    description: str
    schedule: Optional[str] = None


class ScheduleRequest(BaseModel):
    """Request model for scheduling a task."""
    schedule: str


class TaskResponse(BaseModel):
    """Response model for a task."""
    id: str
    name: str
    description: str
    status: str
    progress: int
    created_at: str
    updated_at: str
    result: Optional[str] = None
    error: Optional[str] = None
    artifacts: List[str] = []
    schedule: Optional[str] = None
    next_run_time: Optional[str] = None


class ScheduleResponse(BaseModel):
    """Response model for a schedule."""
    task_id: str
    schedule_type: str
    schedule_value: str
    human_readable: str
    next_run_time: Optional[str] = None


class TaskRunResponse(BaseModel):
    """Response model for a task run."""
    id: int
    task_id: str
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error: Optional[str] = None


def create_app(agent: ScoutAgent, scheduler: TaskScheduler) -> FastAPI:
    """
    Create the FastAPI application.
    
    Args:
        agent: The Scout agent
        scheduler: The task scheduler
        
    Returns:
        The FastAPI application
    """
    logger = get_logger(__name__)
    
    app = FastAPI(
        title="Local Scout AI Agent",
        description="API for the Local Scout AI Agent",
        version="1.0.0"
    )
    
    # Configure CORS
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8001,http://127.0.0.1:8001").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Serve static files
    app.mount("/static", StaticFiles(directory="web/static"), name="static")
    
    # Optional API key authentication
    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
    
    def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> bool:
        """
        Verify the API key.
        
        Args:
            api_key: The API key from the request header
            
        Returns:
            True if the API key is valid, False otherwise
        """
        configured_api_key = os.getenv("API_KEY")
        
        # If no API key is configured, allow all requests
        if not configured_api_key:
            return True
        
        # Otherwise, check the API key
        return api_key == configured_api_key
    
    def api_key_required(api_key_valid: bool = Depends(verify_api_key)):
        """
        Dependency to require a valid API key.
        
        Args:
            api_key_valid: Whether the API key is valid
            
        Raises:
            HTTPException: If the API key is invalid
        """
        if not api_key_valid:
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Connected WebSocket clients
    websocket_clients: List[WebSocket] = []
    
    # Register a task listener to send task updates to WebSocket clients
    def task_listener(task: AgentTask):
        """
        Send task updates to WebSocket clients.
        
        Args:
            task: The updated task
        """
        for client in websocket_clients:
            try:
                asyncio.create_task(client.send_text(json.dumps({
                    "type": "task_update",
                    "task": task_to_response(task).dict()
                })))
            except:
                # Client may have disconnected
                pass
    
    # Register the task listener with the agent
    agent.add_task_listener(task_listener)
    
    # Register a scheduler listener to send schedule updates to WebSocket clients
    def scheduler_listener(event: Dict[str, Any]):
        """
        Send scheduler events to WebSocket clients.
        
        Args:
            event: The scheduler event
        """
        for client in websocket_clients:
            try:
                asyncio.create_task(client.send_text(json.dumps(event)))
            except:
                # Client may have disconnected
                pass
    
    # Register the scheduler listener with the scheduler
    scheduler.add_listener(scheduler_listener)
    
    def task_to_response(task: AgentTask) -> TaskResponse:
        """
        Convert an AgentTask to a TaskResponse.
        
        Args:
            task: The agent task
            
        Returns:
            The task response
        """
        return TaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            status=task.status,
            progress=task.progress,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            result=task.result,
            error=task.error,
            artifacts=task.artifacts,
            schedule=task.schedule,
            next_run_time=task.next_run_time.isoformat() if task.next_run_time else None
        )
    
    @app.get("/")
    async def get_index():
        """Serve the index page."""
        return FileResponse("web/templates/index.html")
    
    @app.post("/api/chat", dependencies=[Depends(api_key_required)])
    async def process_input(request: ProcessInputRequest) -> AgentResponse:
        """
        Process user input.
        
        Args:
            request: The input request
            
        Returns:
            The agent response
        """
        try:
            response = await agent.process_input(request.input, request.session_id)
            return response
        except Exception as e:
            logger.error(f"Error processing input: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/tasks", dependencies=[Depends(api_key_required)])
    async def create_task(request: TaskRequest) -> TaskResponse:
        """
        Create a new task.
        
        Args:
            request: The task request
            
        Returns:
            The created task
        """
        try:
            # Create a task
            task = AgentTask(
                name=request.name,
                description=request.description
            )
            agent.tasks[task.id] = task
            
            # Notify the task listeners
            agent._notify_task_listeners(task)
            
            # Schedule the task if requested
            if request.schedule:
                scheduler.schedule_task(task.id, request.schedule)
            else:
                # Otherwise, execute it immediately
                asyncio.create_task(agent._execute_task(task, "api"))
            
            return task_to_response(task)
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/tasks", dependencies=[Depends(api_key_required)])
    async def get_tasks() -> List[TaskResponse]:
        """
        Get all tasks.
        
        Returns:
            A list of tasks
        """
        try:
            return [task_to_response(task) for task in agent.tasks.values()]
        except Exception as e:
            logger.error(f"Error getting tasks: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/tasks/{task_id}", dependencies=[Depends(api_key_required)])
    async def get_task(task_id: str) -> TaskResponse:
        """
        Get a specific task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task
        """
        try:
            if task_id not in agent.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            return task_to_response(agent.tasks[task_id])
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting task: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/tasks/{task_id}/schedule", dependencies=[Depends(api_key_required)])
    async def schedule_task(task_id: str, request: ScheduleRequest) -> Dict[str, Any]:
        """
        Schedule a task.
        
        Args:
            task_id: The task ID
            request: The schedule request
            
        Returns:
            The schedule information
        """
        try:
            if task_id not in agent.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            success = scheduler.schedule_task(task_id, request.schedule)
            
            if not success:
                raise HTTPException(status_code=400, detail="Failed to schedule task")
            
            schedule = scheduler.get_task_schedule(task_id)
            
            if not schedule:
                raise HTTPException(status_code=500, detail="Failed to get schedule information")
            
            return {
                "success": True,
                "schedule": schedule
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error scheduling task: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/tasks/{task_id}/schedule", dependencies=[Depends(api_key_required)])
    async def cancel_task_schedule(task_id: str) -> Dict[str, Any]:
        """
        Cancel a task schedule.
        
        Args:
            task_id: The task ID
            
        Returns:
            Success status
        """
        try:
            if task_id not in agent.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            success = scheduler.cancel_task(task_id)
            
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
    
    @app.get("/api/tasks/{task_id}/schedule", dependencies=[Depends(api_key_required)])
    async def get_task_schedule(task_id: str) -> Dict[str, Any]:
        """
        Get a task's schedule.
        
        Args:
            task_id: The task ID
            
        Returns:
            The schedule information
        """
        try:
            if task_id not in agent.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            schedule = scheduler.get_task_schedule(task_id)
            
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
    
    @app.get("/api/tasks/{task_id}/runs", dependencies=[Depends(api_key_required)])
    async def get_task_runs(task_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get a task's execution history.
        
        Args:
            task_id: The task ID
            limit: Maximum number of runs to return
            
        Returns:
            The task runs
        """
        try:
            if task_id not in agent.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            runs = scheduler.get_task_runs(task_id, limit)
            
            return {
                "success": True,
                "runs": runs
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting task runs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/tasks/{task_id}/artifacts/{artifact_index}", dependencies=[Depends(api_key_required)])
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
            if task_id not in agent.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            task = agent.tasks[task_id]
            
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
    
    @app.delete("/api/tasks/{task_id}", dependencies=[Depends(api_key_required)])
    async def delete_task(task_id: str):
        """
        Delete a specific task.
        
        Args:
            task_id: The task ID
            
        Returns:
            A success message
        """
        try:
            if task_id not in agent.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            # Cancel any scheduled executions
            scheduler.cancel_task(task_id)
            
            # Remove the task
            del agent.tasks[task_id]
            
            return {"success": True, "message": "Task deleted"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting task: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/schedules", dependencies=[Depends(api_key_required)])
    async def get_all_schedules() -> Dict[str, Any]:
        """
        Get all scheduled tasks.
        
        Returns:
            A dictionary of schedules
        """
        try:
            schedules = scheduler.get_all_schedules()
            
            return {
                "success": True,
                "schedules": schedules
            }
        except Exception as e:
            logger.error(f"Error getting schedules: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.websocket("/api/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for real-time updates.
        
        Args:
            websocket: The WebSocket connection
        """
        await websocket.accept()
        websocket_clients.append(websocket)
        
        try:
            # Send current tasks as an initial state
            tasks = [task_to_response(task).dict() for task in agent.tasks.values()]
            await websocket.send_text(json.dumps({
                "type": "initial_state",
                "tasks": tasks
            }))
            
            # Send current schedules
            schedules = scheduler.get_all_schedules()
            await websocket.send_text(json.dumps({
                "type": "schedules",
                "schedules": schedules
            }))
            
            # Wait for messages from the client
            while True:
                data = await websocket.receive_text()
                # Process any client messages if needed
        except WebSocketDisconnect:
            websocket_clients.remove(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            if websocket in websocket_clients:
                websocket_clients.remove(websocket)
    
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    return app