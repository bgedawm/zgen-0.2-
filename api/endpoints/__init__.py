"""
API Endpoints Package
-------------------
This package contains all API endpoints organized by functionality.
"""

from .task_endpoints import router as task_router
from .schedule_endpoints import router as schedule_router
from .chat_endpoints import router as chat_router
from .tool_endpoints import router as tool_router
from .system_endpoints import router as system_router

__all__ = ['task_router', 'schedule_router', 'chat_router', 'tool_router', 'system_router']