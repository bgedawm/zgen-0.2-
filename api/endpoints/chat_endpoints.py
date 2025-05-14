"""
Chat API Endpoints
--------------
This module contains all API endpoints related to chat functionality.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, File, UploadFile, Form

# Setup logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# This will be initialized when the app is created
agent = None


def get_agent():
    if agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return agent


@router.post("/")
async def process_input(
    input: str = Form(...),
    session_id: Optional[str] = Form("default"),
    files: List[UploadFile] = File([])
):
    """
    Process user input and generate a response.
    
    Args:
        input: The user's input message
        session_id: The session ID for conversation tracking
        files: Optional files to include with the message
        
    Returns:
        The agent's response
    """
    try:
        # Save any uploaded files
        attachments = []
        
        if files:
            file_dir = os.path.join("data", "uploads", session_id)
            os.makedirs(file_dir, exist_ok=True)
            
            for file in files:
                file_path = os.path.join(file_dir, file.filename)
                
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                
                attachments.append(file_path)
        
        # Process input through the agent
        response = await get_agent().process_input(input, session_id, attachments)
        
        # Convert response to dict for JSON serialization
        return {
            "message": response.message,
            "task_id": response.task_id,
            "attachments": response.attachments,
            "status": response.status,
            "needs_input": response.needs_input
        }
    except Exception as e:
        logger.error(f"Error processing input: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_sessions():
    """
    Get all active chat sessions.
    
    Returns:
        A list of session IDs
    """
    try:
        sessions = list(get_agent().conversations.keys())
        
        return {
            "success": True,
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Error getting sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a chat session.
    
    Args:
        session_id: The session ID
        
    Returns:
        Success status
    """
    try:
        if session_id in get_agent().conversations:
            del get_agent().conversations[session_id]
        
        return {
            "success": True,
            "message": f"Session {session_id} deleted"
        }
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """
    Get chat history for a session.
    
    Args:
        session_id: The session ID
        
    Returns:
        The chat history
    """
    try:
        if session_id not in get_agent().conversations:
            return {
                "success": True,
                "messages": []
            }
        
        conversation = get_agent().conversations[session_id]
        messages = []
        
        for message in conversation.chat_memory.messages:
            messages.append({
                "role": "user" if hasattr(message, "type") and message.type == "human" else "assistant",
                "content": message.content
            })
        
        return {
            "success": True,
            "messages": messages
        }
    except Exception as e:
        logger.error(f"Error getting session history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))