"""
Node status reporting implementation.
"""

import requests
from datetime import datetime
from typing import Dict, Any, List
from .system_monitor import SystemMonitor

class StatusReporter:
    """
    Handles node status reporting to registry
    """
    
    def __init__(self, registry_url: str, node_id: str, 
                 node_name: str, system_monitor: SystemMonitor):
        """
        Initialize status reporter
        
        Args:
            registry_url: Registry service endpoint
            node_id: Node identifier
            node_name: Node name
            system_monitor: System monitoring instance
        """
        self.registry_url = registry_url
        self.node_id = node_id
        self.node_name = node_name
        self.system_monitor = system_monitor
        self.available_agents: List[str] = []

    def set_available_agents(self, agents: List[str]):
        """
        Update available agents list
        
        Args:
            agents: List of available agent identifiers
        """
        self.available_agents = agents

    def report_status(self):
        """
        Report current node status to registry
        """
        try:
            status = self._prepare_status_report()
            response = self._send_status_report(status)
            
            if response.status_code == 200:
                print(f"Node status reported successfully: {self.node_name}")
                return True
            else:
                print(f"Node status report failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error reporting status: {e}")
            return False

    def _prepare_status_report(self) -> Dict[str, Any]:
        """
        Prepare status report data
        """
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "timestamp": datetime.now().isoformat(),
            "system_info": self.system_monitor.get_system_info(),
            "available_agents": self.available_agents,
            "status": "active"
        }

    def _send_status_report(self, status: Dict[str, Any]) -> requests.Response:
        """
        Send status report to registry
        
        Args:
            status: Status report data
            
        Returns:
            HTTP response from registry
        """
        return requests.post(
            f"{self.registry_url}/api/nodes",
            json=status,
            timeout=5
        ) 