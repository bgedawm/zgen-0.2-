"""
Task Planning Module
-----------------
This module provides task planning capabilities for the agent.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union

from langchain.llms.base import LLM
from langchain.schema import LLMResult
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from utils.logger import get_logger


class TaskPlanner:
    """Provides task planning capabilities for the agent."""
    
    def __init__(self, llm: LLM):
        """
        Initialize the task planner.
        
        Args:
            llm: The LLM instance
        """
        self.logger = get_logger(__name__)
        self.llm = llm
        
        # Initialize prompt templates
        self._initialize_prompts()
        
        self.logger.info("Task planner initialized")
    
    def _initialize_prompts(self):
        """Initialize prompt templates."""
        # Prompt for analyzing if input is a task request
        self.analyze_prompt = PromptTemplate(
            input_variables=["input"],
            template="""
You are Scout, an AI agent designed to help users with various tasks.

I need you to analyze the following user input and determine if it's a request for a task.
A task is something that would take more than a simple answer - it requires research, data analysis, 
creating content, or executing a specific procedure. Tasks usually need planning and execution.

User input: {input}

First, think step by step about whether this is a task request or just a question for information.

If it's a task request, respond in the following JSON format:
```json
{{
  "is_task": true,
  "task_name": "Brief name for the task",
  "task_description": "Detailed description of what the task involves"
}}
```

If it's NOT a task request, respond in the following JSON format:
```json
{{
  "is_task": false
}}
```

Your analysis:
"""
        )
        
        # Prompt for creating a plan for a task
        self.plan_prompt = PromptTemplate(
            input_variables=["task_name", "task_description"],
            template="""
You are Scout, an AI agent designed to help users with various tasks.

I need you to create a detailed plan for the following task:

Task name: {task_name}
Task description: {task_description}

Create a step-by-step plan to complete this task. Think about all the major steps needed,
any information or resources required, and potential challenges. 

Your plan should be in the following JSON format:
```json
{{
  "task_name": "{task_name}",
  "steps": [
    {{
      "step_number": 1,
      "step_name": "Name of the first step",
      "step_description": "Detailed description of what this step involves",
      "estimated_duration": "Estimated time to complete this step (e.g., '5 minutes', '1 hour')",
      "resources_needed": ["Resource 1", "Resource 2"],
      "success_criteria": "How to know when this step is complete"
    }},
    ...additional steps...
  ],
  "estimated_total_duration": "Estimated total time to complete the task",
  "prerequisites": ["Prerequisite 1", "Prerequisite 2"],
  "potential_challenges": ["Challenge 1", "Challenge 2"]
}}
```

Your plan:
"""
        )
    
    async def analyze_input(self, user_input: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Analyze user input to determine if it's a task request.
        
        Args:
            user_input: The user's input
            
        Returns:
            A tuple of (is_task, task_info)
        """
        self.logger.debug(f"Analyzing input: {user_input[:50]}...")
        
        try:
            # Create and run the chain
            chain = LLMChain(
                llm=self.llm,
                prompt=self.analyze_prompt
            )
            
            result = chain.run(input=user_input)
            self.logger.debug(f"Analysis result: {result}")
            
            # Parse the JSON response
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                self.logger.warning("Could not find JSON in analysis result")
                return False, None
            
            json_str = result[json_start:json_end]
            analysis = json.loads(json_str)
            
            is_task = analysis.get("is_task", False)
            
            if is_task:
                task_info = {
                    "name": analysis.get("task_name", "Untitled Task"),
                    "description": analysis.get("task_description", user_input)
                }
                return True, task_info
            else:
                return False, None
        
        except Exception as e:
            self.logger.error(f"Error analyzing input: {str(e)}")
            return False, None
    
    async def create_plan(self, task_name: str, task_description: str) -> Optional[Dict[str, Any]]:
        """
        Create a plan for a task.
        
        Args:
            task_name: The name of the task
            task_description: The description of the task
            
        Returns:
            A plan for the task
        """
        self.logger.info(f"Creating plan for task: {task_name}")
        
        try:
            # Create and run the chain
            chain = LLMChain(
                llm=self.llm,
                prompt=self.plan_prompt
            )
            
            result = chain.run(task_name=task_name, task_description=task_description)
            
            # Parse the JSON response
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                self.logger.warning("Could not find JSON in plan result")
                return None
            
            json_str = result[json_start:json_end]
            plan = json.loads(json_str)
            
            return plan
        
        except Exception as e:
            self.logger.error(f"Error creating plan: {str(e)}")
            return None
    
    async def revise_plan(self, plan: Dict[str, Any], feedback: str) -> Optional[Dict[str, Any]]:
        """
        Revise a plan based on feedback.
        
        Args:
            plan: The current plan
            feedback: Feedback for revision
            
        Returns:
            A revised plan
        """
        self.logger.info("Revising plan based on feedback")
        
        revise_prompt = PromptTemplate(
            input_variables=["plan", "feedback"],
            template="""
You are Scout, an AI agent designed to help users with various tasks.

I need you to revise the following task plan based on user feedback:

Current plan:
{plan}

User feedback:
{feedback}

Please revise the plan accordingly and return the updated plan in the same JSON format.

Your revised plan:
"""
        )
        
        try:
            # Create and run the chain
            chain = LLMChain(
                llm=self.llm,
                prompt=revise_prompt
            )
            
            result = chain.run(plan=json.dumps(plan, indent=2), feedback=feedback)
            
            # Parse the JSON response
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                self.logger.warning("Could not find JSON in revised plan result")
                return None
            
            json_str = result[json_start:json_end]
            revised_plan = json.loads(json_str)
            
            return revised_plan
        
        except Exception as e:
            self.logger.error(f"Error revising plan: {str(e)}")
            return None