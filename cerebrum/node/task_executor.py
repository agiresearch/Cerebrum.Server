"""
Task execution implementation.
"""

import sys
import subprocess
import ast
from typing import Dict, Any, List, Optional

class TaskExecutor:
    """
    Handles task execution and processing
    """
    
    def __init__(self, default_llm: str = "gpt-4o-mini"):
        """
        Initialize task executor
        
        Args:
            default_llm: Default LLM model to use
        """
        self.default_llm = default_llm
    
    def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task
        
        Args:
            task_data: Task definition and parameters
            
        Returns:
            Task execution results
        """
        if isinstance(task_data, dict) and task_data.get('type') == 'custom':
            return self._execute_custom_task(task_data)
            
        return {
            "status": "completed",
            "message": "Non-custom task completed"
        }

    def _execute_custom_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute custom agent task
        
        Args:
            task_data: Task parameters
            
        Returns:
            Execution results
        """
        data = task_data.get('data', {})
        message = data.get('message', '')
        agent_name = data.get('agent', '')
        
        if not message:
            return {
                "status": "failed",
                "message": "Missing task content"
            }
            
        return self._run_agent(agent_name, message)

    def _run_agent(self, agent_name: str, message: str) -> Dict[str, Any]:
        """
        Run agent with specified parameters
        
        Args:
            agent_name: Agent identifier
            message: Task message
            
        Returns:
            Agent execution results
        """
        try:
            agent_name = self._ensure_full_agent_path(agent_name)
            cmd = self._build_agent_command(agent_name, message)
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                return self._parse_agent_output(process.stdout)
            else:
                return {
                    "status": "failed",
                    "message": "Agent execution failed",
                    "error": process.stderr
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "message": "Error during execution",
                "error": str(e)
            }

    def _ensure_full_agent_path(self, agent: str) -> str:
        """
        Ensure agent name includes full path
        """
        if agent and '/' not in agent:
            return f"example/{agent}"
        return agent

    def _build_agent_command(self, agent_name: str, message: str) -> List[str]:
        """
        Build agent execution command
        """
        # Use default LLM model set during registration
        llm_name = self.default_llm
        
        print(f"Using model: {llm_name}, agent: {agent_name}, message: {message}")
        
        # Check if it's gemini-1.5-flash model
        if llm_name == "gemini-1.5-flash":
            return [
                sys.executable,
                "-m", "cerebrum.example.run_agent",
                "--llm_name", "gemini-1.5-flash",
                "--llm_backend", "google",
                "--agent_name_or_path", agent_name,
                "--task", message if isinstance(message, str) else str(message),
                "--aios_kernel_url", "http://localhost:8000"
            ]
        else:
            # Default to OpenAI backend
            return [
                sys.executable,
                "-m", "cerebrum.example.run_agent",
                "--llm_name", llm_name,
                "--llm_backend", "openai",
                "--agent_name_or_path", agent_name,
                "--task", message if isinstance(message, str) else str(message),
                "--aios_kernel_url", "http://localhost:8000"
            ]

    def _parse_agent_output(self, output: str) -> Dict[str, Any]:
        """
        Parse agent execution output
        """
        try:
            if "Final Result:" in output:
                result_text = output.split("Final Result:", 1)[1].strip()
                result_dict = ast.literal_eval(result_text)
                return {
                    "status": "completed",
                    "result": result_dict.get('result', '')
                }
            return {
                "status": "failed",
                "message": "No execution result found"
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": str(e)
            }