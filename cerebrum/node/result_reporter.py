"""
Task result reporting implementation.
"""

import requests
from typing import Dict, Any

class ResultReporter:
    """
    Handles task result reporting
    """
    
    def __init__(self, registry_url: str, node_id: str):
        """
        Initialize result reporter
        
        Args:
            registry_url: Registry service endpoint
            node_id: Node identifier
        """
        self.registry_url = registry_url
        self.node_id = node_id

    def report_result(self, task_id: str, result: Dict[str, Any]):
        """
        Report task execution result
        
        Args:
            task_id: Task identifier
            result: Task execution result
        """
        try:
            data = self._prepare_result_data(task_id, result)
            response = self._send_result(data)
            
            if response.status_code == 200:
                print(f"Task result reported successfully: {task_id}")
            else:
                print(f"Task result report failed: {response.status_code}")
                
        except Exception as e:
            print(f"Error reporting result: {e}")

    def report_error(self, task_id: str, error: str):
        """
        Report task execution error
        
        Args:
            task_id: Task identifier
            error: Error message
        """
        result = {
            "status": "failed",
            "message": "System error",
            "error": error
        }
        self.report_result(task_id, result)

    def _prepare_result_data(self, task_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare result report data
        """
        return {
            "taskId": task_id,
            "nodeId": self.node_id,
            "result": result
        }

    def _send_result(self, data: Dict[str, Any]) -> requests.Response:
        """
        Send result to registry
        """
        return requests.post(
            f"{self.registry_url}/api/nodes/results",
            json=data,
            timeout=5
        ) 