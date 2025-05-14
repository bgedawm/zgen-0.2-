"""
File Tools Module
--------------
This module provides file-related tools for the agent.
"""

import os
import shutil
import json
import logging
import mimetypes
from typing import Dict, List, Any, Optional
from pathlib import Path

from utils.logger import get_logger


class FileTools:
    """Provides file-related tools for the agent."""
    
    def __init__(self):
        """Initialize the file tools."""
        self.logger = get_logger(__name__)
    
    async def read_file(self, path: str) -> Dict[str, Any]:
        """
        Read a file and return its contents.
        
        Args:
            path: The path to the file
            
        Returns:
            A dictionary with the file content and metadata
        """
        file_path = Path(path)
        
        try:
            # Check if the file exists
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }
            
            # Get file info
            stat_info = file_path.stat()
            
            # Determine file type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # For text files, read the content
            if mime_type is None or mime_type.startswith("text/") or mime_type in [
                "application/json", "application/xml", "application/javascript"
            ]:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                return {
                    "success": True,
                    "content": content,
                    "mime_type": mime_type or "text/plain",
                    "size": stat_info.st_size,
                    "is_text": True
                }
            else:
                # For binary files, just return metadata
                return {
                    "success": True,
                    "content": f"[Binary file of type {mime_type}]",
                    "mime_type": mime_type,
                    "size": stat_info.st_size,
                    "is_text": False
                }
        
        except Exception as e:
            self.logger.error(f"Error reading file {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file.
        
        Args:
            path: The path to the file
            content: The content to write
            
        Returns:
            A dictionary with the result
        """
        file_path = Path(path)
        
        try:
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return {
                "success": True,
                "path": str(file_path),
                "size": file_path.stat().st_size
            }
        
        except Exception as e:
            self.logger.error(f"Error writing file {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def append_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Append content to a file.
        
        Args:
            path: The path to the file
            content: The content to append
            
        Returns:
            A dictionary with the result
        """
        file_path = Path(path)
        
        try:
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Append the content
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)
            
            return {
                "success": True,
                "path": str(file_path),
                "size": file_path.stat().st_size
            }
        
        except Exception as e:
            self.logger.error(f"Error appending to file {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_directory(self, path: str = ".") -> Dict[str, Any]:
        """
        List the contents of a directory.
        
        Args:
            path: The path to the directory
            
        Returns:
            A dictionary with the directory contents
        """
        dir_path = Path(path)
        
        try:
            # Check if the directory exists
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {path}"
                }
            
            # Check if it's a directory
            if not dir_path.is_dir():
                return {
                    "success": False,
                    "error": f"Not a directory: {path}"
                }
            
            # List the contents
            contents = []
            for item in dir_path.iterdir():
                stat_info = item.stat()
                contents.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": stat_info.st_size,
                    "modified": stat_info.st_mtime
                })
            
            return {
                "success": True,
                "path": str(dir_path),
                "contents": contents
            }
        
        except Exception as e:
            self.logger.error(f"Error listing directory {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_file(self, path: str) -> Dict[str, Any]:
        """
        Delete a file or directory.
        
        Args:
            path: The path to the file or directory
            
        Returns:
            A dictionary with the result
        """
        item_path = Path(path)
        
        try:
            # Check if the item exists
            if not item_path.exists():
                return {
                    "success": False,
                    "error": f"File or directory not found: {path}"
                }
            
            # Delete the item
            if item_path.is_dir():
                shutil.rmtree(item_path)
            else:
                item_path.unlink()
            
            return {
                "success": True,
                "path": str(item_path),
                "is_dir": item_path.is_dir()
            }
        
        except Exception as e:
            self.logger.error(f"Error deleting {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_directory(self, path: str) -> Dict[str, Any]:
        """
        Create a directory.
        
        Args:
            path: The path to the directory
            
        Returns:
            A dictionary with the result
        """
        dir_path = Path(path)
        
        try:
            # Create the directory
            dir_path.mkdir(parents=True, exist_ok=True)
            
            return {
                "success": True,
                "path": str(dir_path)
            }
        
        except Exception as e:
            self.logger.error(f"Error creating directory {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def move_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Move a file or directory.
        
        Args:
            source: The source path
            destination: The destination path
            
        Returns:
            A dictionary with the result
        """
        source_path = Path(source)
        dest_path = Path(destination)
        
        try:
            # Check if the source exists
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source not found: {source}"
                }
            
            # Create parent directories if they don't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the item
            if source_path.is_dir():
                if dest_path.exists():
                    # If the destination exists, we'll merge the directories
                    for item in source_path.iterdir():
                        shutil.move(str(item), str(dest_path / item.name))
                else:
                    # Otherwise, move the whole directory
                    shutil.move(str(source_path), str(dest_path))
            else:
                shutil.move(str(source_path), str(dest_path))
            
            return {
                "success": True,
                "source": str(source_path),
                "destination": str(dest_path)
            }
        
        except Exception as e:
            self.logger.error(f"Error moving {source} to {destination}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def copy_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Copy a file or directory.
        
        Args:
            source: The source path
            destination: The destination path
            
        Returns:
            A dictionary with the result
        """
        source_path = Path(source)
        dest_path = Path(destination)
        
        try:
            # Check if the source exists
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source not found: {source}"
                }
            
            # Create parent directories if they don't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the item
            if source_path.is_dir():
                if dest_path.exists() and dest_path.is_dir():
                    # If the destination exists and is a directory, copy the contents
                    for item in source_path.iterdir():
                        if item.is_dir():
                            shutil.copytree(str(item), str(dest_path / item.name))
                        else:
                            shutil.copy2(str(item), str(dest_path / item.name))
                else:
                    # Otherwise, copy the whole directory
                    shutil.copytree(str(source_path), str(dest_path))
            else:
                shutil.copy2(str(source_path), str(dest_path))
            
            return {
                "success": True,
                "source": str(source_path),
                "destination": str(dest_path)
            }
        
        except Exception as e:
            self.logger.error(f"Error copying {source} to {destination}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


def get_file_tools() -> Dict[str, Any]:
    """
    Get the file tools.
    
    Returns:
        A dictionary of file tool functions
    """
    tools = FileTools()
    
    return {
        "read_file": tools.read_file,
        "write_file": tools.write_file,
        "append_file": tools.append_file,
        "list_directory": tools.list_directory,
        "delete_file": tools.delete_file,
        "create_directory": tools.create_directory,
        "move_file": tools.move_file,
        "copy_file": tools.copy_file
    }