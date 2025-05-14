"""
Tool API Endpoints
---------------
This module contains all API endpoints related to tools.
"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException

# Setup logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])

# This will be initialized when the app is created
agent = None


def get_agent():
    if agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return agent


@router.get("/")
async def get_tools():
    """
    Get all available tools.
    
    Returns:
        A list of tools
    """
    try:
        tools = []
        
        for tool_name, tool_func in get_agent().tools.items():
            # Get tool documentation
            doc = tool_func.__doc__ or "No description available"
            
            # Determine tool category
            category = "other"
            if tool_name.startswith("file_"):
                category = "file"
            elif tool_name.startswith("web_"):
                category = "web"
            elif tool_name.startswith("code_"):
                category = "code"
            elif tool_name.startswith("data_"):
                category = "data"
            
            # Get tool parameters
            parameters = []
            if hasattr(tool_func, "__annotations__"):
                for param_name, param_type in tool_func.__annotations__.items():
                    if param_name != "return":
                        param_type_str = str(param_type)
                        if "typing." in param_type_str:
                            param_type_str = param_type_str.replace("typing.", "").lower()
                        
                        parameters.append({
                            "name": param_name,
                            "type": param_type_str,
                            "description": f"Parameter {param_name}" # Better descriptions would come from docstrings
                        })
            
            tools.append({
                "name": tool_name,
                "description": doc,
                "category": category,
                "parameters": parameters
            })
        
        return {
            "success": True,
            "tools": tools
        }
    except Exception as e:
        logger.error(f"Error getting tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tool_name}")
async def get_tool(tool_name: str):
    """
    Get details for a specific tool.
    
    Args:
        tool_name: The tool name
        
    Returns:
        The tool details
    """
    try:
        if tool_name not in get_agent().tools:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        tool_func = get_agent().tools[tool_name]
        
        # Get tool documentation
        doc = tool_func.__doc__ or "No description available"
        
        # Determine tool category
        category = "other"
        if tool_name.startswith("file_"):
            category = "file"
        elif tool_name.startswith("web_"):
            category = "web"
        elif tool_name.startswith("code_"):
            category = "code"
        elif tool_name.startswith("data_"):
            category = "data"
        
        # Get tool parameters
        parameters = []
        if hasattr(tool_func, "__annotations__"):
            for param_name, param_type in tool_func.__annotations__.items():
                if param_name != "return":
                    param_type_str = str(param_type)
                    if "typing." in param_type_str:
                        param_type_str = param_type_str.replace("typing.", "").lower()
                    
                    parameters.append({
                        "name": param_name,
                        "type": param_type_str,
                        "description": f"Parameter {param_name}" # Better descriptions would come from docstrings
                    })
        
        return {
            "success": True,
            "tool": {
                "name": tool_name,
                "description": doc,
                "category": category,
                "parameters": parameters
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))