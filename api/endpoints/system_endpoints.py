"""
System API Endpoints
----------------
This module contains system-level API endpoints.
"""

import os
import psutil
import platform
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

# Setup logger
logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

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


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@router.get("/system/info")
async def system_info():
    """
    Get system information.
    
    Returns:
        System information
    """
    try:
        # System info
        system_info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "memory_percent": psutil.virtual_memory().percent,
            "disk_total": psutil.disk_usage('/').total,
            "disk_used": psutil.disk_usage('/').used,
            "disk_free": psutil.disk_usage('/').free,
            "disk_percent": psutil.disk_usage('/').percent
        }
        
        # Agent info
        agent_info = {
            "tasks_count": len(get_agent().tasks),
            "tools_count": len(get_agent().tools),
            "scheduled_tasks_count": len(get_scheduler().scheduled_tasks)
        }
        
        return {
            "success": True,
            "system": system_info,
            "agent": agent_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_logs(limit: int = 100, level: str = "INFO"):
    """
    Get system logs.
    
    Args:
        limit: Maximum number of log entries to return
        level: Minimum log level to return
        
    Returns:
        Log entries
    """
    try:
        # Convert level string to int
        level_map = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        }
        level_int = level_map.get(level.upper(), 20)
        
        # Get log file path
        log_file = os.getenv("LOG_FILE", "data/logs/agent.log")
        
        # Read log file
        logs = []
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                for line in f.readlines()[-limit:]:
                    # Parse log entry
                    parts = line.strip().split(" - ")
                    if len(parts) >= 3:
                        timestamp = parts[0]
                        log_level = parts[1]
                        message = " - ".join(parts[2:])
                        
                        # Check if log level meets minimum
                        if level_map.get(log_level, 0) >= level_int:
                            logs.append({
                                "timestamp": timestamp,
                                "level": log_level,
                                "message": message
                            })
        
        return {
            "success": True,
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))