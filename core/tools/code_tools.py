"""
Code Tools Module
--------------
This module provides code-related tools for the agent.
"""

import os
import sys
import json
import logging
import asyncio
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path

from utils.logger import get_logger


class CodeTools:
    """Provides code-related tools for the agent."""
    
    def __init__(self):
        """Initialize the code tools."""
        self.logger = get_logger(__name__)
        
        # Keep track of running processes
        self.running_processes: Dict[int, asyncio.subprocess.Process] = {}
        
        # Set a timeout for code execution
        self.execution_timeout = 30
    
    async def execute_python(self, code: str, use_file: bool = True, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute Python code.
        
        Args:
            code: The Python code to execute
            use_file: Whether to save the code to a file and execute it
            file_path: The path to save the code to (if use_file is True)
            
        Returns:
            A dictionary with the execution result
        """
        try:
            if use_file:
                # Save the code to a file
                if file_path is None:
                    file_path = "temp_script.py"
                
                script_path = Path(file_path)
                script_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(code)
                
                # Execute the script
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, str(script_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=os.environ.copy()
                )
            else:
                # Execute the code directly
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-c", code,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=os.environ.copy()
                )
            
            # Store the process
            pid = proc.pid
            self.running_processes[pid] = proc
            
            # Wait for the process to complete with a timeout
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), self.execution_timeout)
                stdout_text = stdout.decode("utf-8", errors="replace")
                stderr_text = stderr.decode("utf-8", errors="replace")
                
                # Remove the process from the list
                if pid in self.running_processes:
                    del self.running_processes[pid]
                
                return {
                    "success": proc.returncode == 0,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "returncode": proc.returncode,
                    "pid": pid,
                    "file_path": str(script_path) if use_file else None
                }
            
            except asyncio.TimeoutError:
                # Timeout exceeded, kill the process
                proc.terminate()
                return {
                    "success": False,
                    "error": f"Execution timed out after {self.execution_timeout} seconds",
                    "pid": pid,
                    "file_path": str(script_path) if use_file else None
                }
        
        except Exception as e:
            self.logger.error(f"Error executing Python code: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_javascript(self, code: str, use_file: bool = True, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute JavaScript code using Node.js.
        
        Args:
            code: The JavaScript code to execute
            use_file: Whether to save the code to a file and execute it
            file_path: The path to save the code to (if use_file is True)
            
        Returns:
            A dictionary with the execution result
        """
        try:
            # Check if Node.js is installed
            try:
                proc = await asyncio.create_subprocess_exec(
                    "node", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()
                if proc.returncode != 0:
                    return {
                        "success": False,
                        "error": "Node.js is not installed"
                    }
            except:
                return {
                    "success": False,
                    "error": "Node.js is not installed"
                }
            
            if use_file:
                # Save the code to a file
                if file_path is None:
                    file_path = "temp_script.js"
                
                script_path = Path(file_path)
                script_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(code)
                
                # Execute the script
                proc = await asyncio.create_subprocess_exec(
                    "node", str(script_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=os.environ.copy()
                )
            else:
                # Execute the code directly
                proc = await asyncio.create_subprocess_exec(
                    "node", "-e", code,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=os.environ.copy()
                )
            
            # Store the process
            pid = proc.pid
            self.running_processes[pid] = proc
            
            # Wait for the process to complete with a timeout
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), self.execution_timeout)
                stdout_text = stdout.decode("utf-8", errors="replace")
                stderr_text = stderr.decode("utf-8", errors="replace")
                
                # Remove the process from the list
                if pid in self.running_processes:
                    del self.running_processes[pid]
                
                return {
                    "success": proc.returncode == 0,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "returncode": proc.returncode,
                    "pid": pid,
                    "file_path": str(script_path) if use_file else None
                }
            
            except asyncio.TimeoutError:
                # Timeout exceeded, kill the process
                proc.terminate()
                return {
                    "success": False,
                    "error": f"Execution timed out after {self.execution_timeout} seconds",
                    "pid": pid,
                    "file_path": str(script_path) if use_file else None
                }
        
        except Exception as e:
            self.logger.error(f"Error executing JavaScript code: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_shell(self, command: str) -> Dict[str, Any]:
        """
        Execute a shell command.
        
        Args:
            command: The shell command to execute
            
        Returns:
            A dictionary with the execution result
        """
        try:
            # Execute the command
            proc = await asyncio.create_subprocess_exec(
                "sh", "-c", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            
            # Store the process
            pid = proc.pid
            self.running_processes[pid] = proc
            
            # Wait for the process to complete with a timeout
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), self.execution_timeout)
                stdout_text = stdout.decode("utf-8", errors="replace")
                stderr_text = stderr.decode("utf-8", errors="replace")
                
                # Remove the process from the list
                if pid in self.running_processes:
                    del self.running_processes[pid]
                
                return {
                    "success": proc.returncode == 0,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "returncode": proc.returncode,
                    "pid": pid
                }
            
            except asyncio.TimeoutError:
                # Timeout exceeded, kill the process
                proc.terminate()
                return {
                    "success": False,
                    "error": f"Execution timed out after {self.execution_timeout} seconds",
                    "pid": pid
                }
        
        except Exception as e:
            self.logger.error(f"Error executing shell command: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def terminate_process(self, pid: int) -> Dict[str, Any]:
        """
        Terminate a running process.
        
        Args:
            pid: The process ID
            
        Returns:
            A dictionary with the termination result
        """
        try:
            if pid not in self.running_processes:
                return {
                    "success": False,
                    "error": f"No process with ID {pid} found"
                }
            
            # Terminate the process
            proc = self.running_processes[pid]
            proc.terminate()
            
            # Wait for the process to terminate
            try:
                await asyncio.wait_for(proc.wait(), 5)
            except asyncio.TimeoutError:
                # Force kill the process
                proc.kill()
            
            # Remove the process from the list
            del self.running_processes[pid]
            
            return {
                "success": True,
                "pid": pid
            }
        
        except Exception as e:
            self.logger.error(f"Error terminating process {pid}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def lint_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Lint code for potential issues.
        
        Args:
            code: The code to lint
            language: The programming language
            
        Returns:
            A dictionary with the linting result
        """
        try:
            if language.lower() == "python":
                # Save the code to a temporary file
                temp_file = Path("temp_lint.py")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(code)
                
                # Run a linter (using pyflakes)
                try:
                    proc = await asyncio.create_subprocess_exec(
                        sys.executable, "-m", "pyflakes", str(temp_file),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await proc.communicate()
                    stdout_text = stdout.decode("utf-8", errors="replace")
                    stderr_text = stderr.decode("utf-8", errors="replace")
                    
                    # Parse the output
                    issues = []
                    for line in (stdout_text + stderr_text).splitlines():
                        if line.strip():
                            issues.append(line.strip())
                    
                    # Clean up
                    temp_file.unlink()
                    
                    return {
                        "success": True,
                        "language": language,
                        "issues": issues,
                        "has_issues": len(issues) > 0
                    }
                
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Error running linter: {str(e)}"
                    }
            
            elif language.lower() in ("javascript", "js"):
                # Save the code to a temporary file
                temp_file = Path("temp_lint.js")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(code)
                
                # Run a linter (using eslint)
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "npx", "eslint", str(temp_file),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await proc.communicate()
                    stdout_text = stdout.decode("utf-8", errors="replace")
                    stderr_text = stderr.decode("utf-8", errors="replace")
                    
                    # Parse the output
                    issues = []
                    for line in (stdout_text + stderr_text).splitlines():
                        if line.strip():
                            issues.append(line.strip())
                    
                    # Clean up
                    temp_file.unlink()
                    
                    return {
                        "success": True,
                        "language": language,
                        "issues": issues,
                        "has_issues": len(issues) > 0
                    }
                
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Error running linter: {str(e)}"
                    }
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported language: {language}"
                }
        
        except Exception as e:
            self.logger.error(f"Error linting code: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


def get_code_tools() -> Dict[str, Any]:
    """
    Get the code tools.
    
    Returns:
        A dictionary of code tool functions
    """
    tools = CodeTools()
    
    return {
        "execute_python": tools.execute_python,
        "execute_javascript": tools.execute_javascript,
        "execute_shell": tools.execute_shell,
        "terminate_process": tools.terminate_process,
        "lint_code": tools.lint_code
    }