"""
API Package Initialization
-----------------------
This package provides API endpoints for the agent.
"""

from api.app import create_app

__all__ = [
    "create_app",
]