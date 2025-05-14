"""
Core Agent Module
---------------
This module implements the main Scout-like AI agent functionality.
"""

import os
import uuid
import asyncio
import logging
import traceback
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from datetime import datetime

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel, Field

from core.llm import get_llm

# Import monitoring integration if available
try:
    from core.monitoring import get_agent_monitor, track, track_async
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    # Define placeholder tracking decorators
    def track(name=None, log_level=logging.DEBUG):
        def decorator(func):
            return func
        return decorator
    
    def track_async(name=None, log_level=logging.DEBUG):
        def decorator(func):
            return func
        return decorator
from core.memory import AgentMemory
from core.planning import TaskPlanner
from core.tools.file_tools import get_file_tools
from core.tools.web_tools import get_web_tools
from core.tools.code_tools import get_code_tools
from core.tools.data_tools import get_data_tools
from utils.logger import get_logger, TaskLogger


class AgentTask(BaseModel):
    """Represents a task to be performed by the agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    artifacts: List[str] = Field(default_factory=list)
    progress: int = 0  # 0-100
    # Schedule information
    schedule: Optional[str] = None
    next_run_time: Optional[datetime] = None


class AgentResponse(BaseModel):
    """Represents a response from the agent."""
    message: str
    task_id: Optional[str] = None
    attachments: List[str] = []
    status: str = "success"
    needs_input: bool = False


class TaskExecutor:
    """Executes tasks for the agent."""
    
    def __init__(self, agent: 'ScoutAgent', task: AgentTask, session_id: str):
        """
        Initialize the task executor.
        
        Args:
            agent: The Scout agent
            task: The task to execute
            session_id: The session ID
        """
        self.agent = agent
        self.task = task
        self.session_id = session_id
        self.logger = TaskLogger(task.id)
        
        # Task-specific memory
        self.memory = ConversationBufferMemory(return_messages=True)
        
        # Create task-specific prompt templates
        self._initialize_prompts()
    
    def _initialize_prompts(self):
        """Initialize prompt templates for task execution."""
        # Main task execution prompt
        self.execution_prompt = PromptTemplate(
            input_variables=["task_name", "task_description", "plan", "memory", "available_tools"],
            template="""
You are Scout, an AI agent designed to help users with various tasks.

You are currently working on the following task:
Task name: {task_name}
Task description: {task_description}

Your plan for this task:
{plan}

Previous progress:
{memory}

You have access to the following tools to complete this task:
{available_tools}

Think step by step about how to make progress on this task. Use the available tools as needed.
If you need more information from the user, you should ask for it.
If you've completed the task, summarize what you've done and the results.

Your next step:
"""
        )
    
    @track_async(name="task_execution")
    async def execute(self) -> None:
        """Execute the task."""
        self.logger.info(f"Starting execution of task: {self.task.name}")
        
        try:
            # Update task status
            self.task.status = "running"
            self.task.updated_at = datetime.now()
            
            # Notify task listeners
            self.agent._notify_task_listeners(self.task)
            
            # Create a plan for the task
            plan = await self.agent.planner.create_plan(self.task.name, self.task.description)
            
            if not plan:
                self.logger.error("Failed to create a plan for the task")
                self.task.status = "failed"
                self.task.error = "Failed to create a plan for the task"
                self.task.updated_at = datetime.now()
                self.agent._notify_task_listeners(self.task)
                return
            
            self.logger.info(f"Created plan with {len(plan['steps'])} steps")
            
            # Execute each step of the plan
            for i, step in enumerate(plan["steps"]):
                step_number = i + 1
                total_steps = len(plan["steps"])
                
                self.logger.info(f"Executing step {step_number}/{total_steps}: {step['step_name']}")
                
                # Update progress
                self.task.progress = int((i / total_steps) * 100)
                self.task.updated_at = datetime.now()
                self.agent._notify_task_listeners(self.task)
                
                # Add step to memory
                self.memory.chat_memory.add_ai_message(f"Starting step {step_number}/{total_steps}: {step['step_name']}")
                
                # Execute the step
                step_result = await self._execute_step(step, plan)
                
                if step_result.get("success", False):
                    self.logger.info(f"Step {step_number} completed successfully")
                    self.memory.chat_memory.add_ai_message(f"Completed step {step_number}: {step_result.get('result', '')}")
                else:
                    self.logger.error(f"Step {step_number} failed: {step_result.get('error', '')}")
                    self.memory.chat_memory.add_ai_message(f"Failed to complete step {step_number}: {step_result.get('error', '')}")
                    
                    # Attempt to recover or ask for help
                    recovery_result = await self._attempt_recovery(step, step_result)
                    
                    if not recovery_result.get("success", False):
                        self.task.status = "failed"
                        self.task.error = f"Failed at step {step_number}: {step_result.get('error', '')}"
                        self.task.updated_at = datetime.now()
                        self.agent._notify_task_listeners(self.task)
                        return
            
            # Task completed successfully
            self.logger.info("Task completed successfully")
            self.task.status = "completed"
            self.task.result = self._generate_final_report()
            self.task.progress = 100
            self.task.updated_at = datetime.now()
            self.agent._notify_task_listeners(self.task)
        
        except Exception as e:
            self.logger.error(f"Error executing task: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.task.status = "failed"
            self.task.error = str(e)
            self.task.updated_at = datetime.now()
            self.agent._notify_task_listeners(self.task)
    
    @track_async(name="execute_step")
    async def _execute_step(self, step: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single step of the plan.
        
        Args:
            step: The step to execute
            plan: The complete plan
            
        Returns:
            A dictionary with the step result
        """
        try:
            # Prepare the available tools information
            tools_description = "\n".join([f"- {tool_name}: {tool.__doc__ if tool.__doc__ else 'No description'}" 
                                          for tool_name, tool in self.agent.tools.items()])
            
            # Create the execution chain
            chain = LLMChain(
                llm=self.agent.llm,
                prompt=self.execution_prompt
            )
            
            # Run the chain to get the next action
            memory_str = self.memory.chat_memory.messages_to_string()
            
            action = chain.run(
                task_name=self.task.name,
                task_description=self.task.description,
                plan=step["step_description"],
                memory=memory_str,
                available_tools=tools_description
            )
            
            self.logger.debug(f"Action: {action}")
            
            # Parse and execute the action
            tool_name, tool_args = self._parse_action(action)
            
            if tool_name:
                # Check if the tool exists
                if tool_name in self.agent.tools:
                    # Execute the tool
                    tool = self.agent.tools[tool_name]
                    tool_result = await tool(**tool_args)
                    
                    # Check if an artifact was created
                    if "output_path" in tool_result and tool_result.get("success", False):
                        self.task.artifacts.append(tool_result["output_path"])
                    elif "path" in tool_result and tool_result.get("success", False):
                        self.task.artifacts.append(tool_result["path"])
                    
                    return {
                        "success": tool_result.get("success", False),
                        "result": str(tool_result),
                        "error": tool_result.get("error", None)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Tool not found: {tool_name}"
                    }
            else:
                # No specific tool was used, consider the step completed
                return {
                    "success": True,
                    "result": action
                }
        
        except Exception as e:
            self.logger.error(f"Error executing step: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_action(self, action: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Parse an action string to extract tool name and arguments.
        
        Args:
            action: The action string
            
        Returns:
            A tuple of (tool_name, tool_args)
        """
        import re
        
        # Look for tool invocations in the format: use_tool(arg1="value1", arg2="value2")
        tool_pattern = r'use_(\w+)\((.*?)\)'
        tool_match = re.search(tool_pattern, action, re.DOTALL)
        
        if not tool_match:
            return None, {}
        
        tool_name = tool_match.group(1)
        args_str = tool_match.group(2)
        
        # Parse the arguments
        args = {}
        
        # Match key-value pairs like key="value" or key=value
        arg_pattern = r'(\w+)=(?:"([^"]*)"|([\w.]*))'
        for arg_match in re.finditer(arg_pattern, args_str):
            key = arg_match.group(1)
            # Get either the quoted value or the non-quoted value
            value = arg_match.group(2) if arg_match.group(2) is not None else arg_match.group(3)
            args[key] = value
        
        return tool_name, args
    
    async def _attempt_recovery(self, step: Dict[str, Any], step_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt to recover from a failed step.
        
        Args:
            step: The failed step
            step_result: The result of the failed step
            
        Returns:
            A dictionary with the recovery result
        """
        self.logger.info("Attempting to recover from a failed step")
        
        # For now, we'll just return success=False to indicate that recovery failed
        # In a real system, you would implement more sophisticated recovery strategies
        
        return {
            "success": False,
            "error": step_result.get("error", "Unknown error")
        }
    
    def _generate_final_report(self) -> str:
        """
        Generate a final report for the task.
        
        Returns:
            The final report
        """
        # Extract messages from memory
        memory_str = self.memory.chat_memory.messages_to_string()
        
        # List artifacts
        artifacts_str = ""
        if self.task.artifacts:
            artifacts_str = "Artifacts created:\n" + "\n".join([f"- {artifact}" for artifact in self.task.artifacts])
        
        # Generate the report
        report = f"""
Task Summary: {self.task.name}
-----------------------
{self.task.description}

Execution Timeline:
{memory_str}

{artifacts_str}

Task completed successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return report


class ScoutAgent:
    """
    Scout-like AI Agent that can perform various tasks.
    """
    
    def __init__(self):
        """Initialize the Scout Agent."""
        self.logger = get_logger(__name__)
        self.logger.info("Initializing Scout Agent...")
        
        # Initialize LLM
        self.llm = get_llm()
        
        # Initialize memory
        self.memory = AgentMemory()
        
        # Initialize task planner
        self.planner = TaskPlanner(self.llm)
        
        # Initialize tools
        self.tools = {}
        self._initialize_tools()
        
        # Task tracking
        self.tasks: Dict[str, AgentTask] = {}
        
        # Initialize monitoring
        if MONITORING_AVAILABLE:
            self.logger.info("Initializing agent monitoring...")
            self.monitor = get_agent_monitor()
        else:
            self.logger.warning("Agent monitoring not available")
        
        # Conversation memory for each session
        self.conversations: Dict[str, ConversationBufferMemory] = {}
        
        # Event listeners
        self.task_listeners: List[Callable[[AgentTask], None]] = []
        
        self.logger.info("Scout Agent initialized successfully")
    
    def _initialize_tools(self):
        """Initialize all available tools."""
        # Load tools based on environment configuration
        if os.getenv("ENABLE_FILE_TOOLS", "True").lower() == "true":
            self.tools.update(get_file_tools())
        
        if os.getenv("ENABLE_WEB_TOOLS", "True").lower() == "true":
            self.tools.update(get_web_tools())
            
        if os.getenv("ENABLE_CODE_TOOLS", "True").lower() == "true":
            self.tools.update(get_code_tools())
            
        if os.getenv("ENABLE_DATA_TOOLS", "True").lower() == "true":
            self.tools.update(get_data_tools())
        
        self.logger.info(f"Initialized {len(self.tools)} tools")
    
    def add_task_listener(self, listener: Callable[[AgentTask], None]):
        """
        Add a task listener.
        
        Args:
            listener: The listener function
        """
        self.task_listeners.append(listener)
    
    def remove_task_listener(self, listener: Callable[[AgentTask], None]):
        """
        Remove a task listener.
        
        Args:
            listener: The listener function
        """
        if listener in self.task_listeners:
            self.task_listeners.remove(listener)
    
    def _notify_task_listeners(self, task: AgentTask):
        """
        Notify all task listeners.
        
        Args:
            task: The updated task
        """
        for listener in self.task_listeners:
            try:
                listener(task)
            except Exception as e:
                self.logger.error(f"Error in task listener: {str(e)}")
    
    @track_async(name="process_input")
    async def process_input(self, user_input: str, session_id: str = "default") -> AgentResponse:
        """
        Process user input and generate a response.
        
        Args:
            user_input: The user's input message
            session_id: The session ID for conversation tracking
            
        Returns:
            An AgentResponse object
        """
        self.logger.info(f"Processing input for session {session_id}: {user_input[:50]}...")
        
        # Create conversation memory if it doesn't exist
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationBufferMemory(return_messages=True)
        
        # Store user input in memory
        memory = self.conversations[session_id]
        memory.chat_memory.add_user_message(user_input)
        
        # Determine if this is a task request
        is_task, task_info = await self.planner.analyze_input(user_input)
        
        if is_task:
            # Create and execute a task
            task = AgentTask(
                name=task_info["name"],
                description=task_info["description"]
            )
            self.tasks[task.id] = task
            
            # Notify task listeners
            self._notify_task_listeners(task)
            
            # Queue the task for execution
            asyncio.create_task(self._execute_task(task, session_id))
            
            response = AgentResponse(
                message=f"I've created task '{task.name}' and started working on it. You can check its status using the task ID: {task.id}",
                task_id=task.id
            )
            
            # Store response in memory
            memory.chat_memory.add_ai_message(response.message)
            
            return response
        else:
            # Handle as a conversation
            prompt = PromptTemplate(
                input_variables=["history", "input"],
                template="""You are Scout, a helpful AI assistant that can perform various tasks.

{history}