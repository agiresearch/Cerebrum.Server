"""
Task management and execution implementation.
"""

import sys
import subprocess
import ast
import requests
from typing import Dict, Any, Optional
from .task_executor import TaskExecutor
from .result_reporter import ResultReporter

class TaskManager:
    """
    Manages task processing and execution
    """
    
    def __init__(self, registry_url: str, node_id: str, default_llm: str = "gpt-4o-mini"):
        """
        Initialize task manager
        
        Args:
            registry_url: Registry service endpoint
            node_id: Node identifier
            default_llm: Default LLM model to use
        """
        self.registry_url = registry_url
        self.node_id = node_id
        self.default_llm = default_llm
        self.task_executor = TaskExecutor(default_llm)
        self.result_reporter = ResultReporter(registry_url, node_id)

    def fetch_pending_tasks(self):
        """
        Fetch pending tasks from registry
        """
        try:
            print(f"Fetching tasks from {self.registry_url}/api/nodes/tasks...")
            print(f"Using node ID: {self.node_id}")
            
            response = self._get_pending_tasks()
            
            # Check response status code
            if response.status_code == 200:
                tasks = response.json()
                print(f"API response: {tasks}")
                
                if tasks and isinstance(tasks, list) and len(tasks) > 0:
                    print(f"Retrieved {len(tasks)} pending tasks")
                    for task in tasks:
                        self.process_task(task)
                else:
                    print("No pending tasks available")
            else:
                print(f"Failed to fetch tasks, status code: {response.status_code}")
                print(f"Response content: {response.text}")
            
        except Exception as e:
            print(f"Error fetching tasks: {str(e)}")
            import traceback
            traceback.print_exc()

    def process_task(self, task: Dict[str, Any]):
        """
        Process a single task
        
        Args:
            task: Task definition and parameters
        """
        try:
            task_id = task.get('taskId')
            task_data = task.get('task')
            
            print(f"Processing task: {task_id}")
            print(f"Task data: {task_data}")
            
            if not task_id:
                print("Task ID is empty, skipping processing")
                return
                
            result = self.task_executor.execute_task(task_data)
            print(f"Task execution result: {result}")
            self.result_reporter.report_result(task_id, result)
            
        except Exception as e:
            print(f"Task processing error: {e}")
            import traceback
            traceback.print_exc()
            if task_id:
                self.result_reporter.report_error(task_id, str(e))

    def _get_pending_tasks(self) -> requests.Response:
        """
        Fetch pending tasks from registry
        """
        url = f"{self.registry_url}/api/nodes/tasks"
        params = {"node_id": self.node_id}
        
        print(f"Sending GET request to: {url}")
        print(f"Request parameters: {params}")
        
        response = requests.get(
            url,
            params=params,
            timeout=5
        )
        
        return response 