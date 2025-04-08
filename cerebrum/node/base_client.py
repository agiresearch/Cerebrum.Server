"""
Base node client implementation providing core functionality.
"""

import threading
import time
import uuid
import platform
from typing import List, Optional
from .system_monitor import SystemMonitor
from .task_manager import TaskManager
from .status_reporter import StatusReporter

class BaseNodeClient:
    """
    Base class for AIOS distributed node client
    """
    
    def __init__(self, registry_url: str, node_name: str = None, report_interval: int = 30, default_llm: str = "gpt-4o-mini"):
        """
        Initialize base node client
        
        Args:
            registry_url: Registry service endpoint
            node_name: Custom node name
            report_interval: Status update frequency in seconds
            default_llm: Default LLM model to use
        """
        self.registry_url = registry_url
        self.node_id = str(uuid.uuid4())
        self.node_name = node_name or platform.node()
        self.report_interval = report_interval
        self.default_llm = default_llm
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.available_agents: List[str] = []
        
        # Initialize components
        self.system_monitor = SystemMonitor()
        self.task_manager = TaskManager(self.registry_url, self.node_id, self.default_llm)
        self.status_reporter = StatusReporter(
            self.registry_url,
            self.node_id,
            self.node_name,
            self.system_monitor
        )

    def set_available_agents(self, agents: List[str]):
        """
        Update available agents list
        
        Args:
            agents: List of available agent identifiers
        """
        self.available_agents = agents
        self.status_reporter.set_available_agents(agents)

    def _run_loop(self):
        """
        Main service loop for periodic status reporting and task fetching
        """
        task_check_counter = 0
        
        while self.running:
            # Report status every iteration
            self.status_reporter.report_status()
            
            # Check for new tasks without waiting
            try:
                print("Checking for new tasks...")
                self.task_manager.fetch_pending_tasks()
            except Exception as e:
                print(f"Error fetching tasks: {e}")
            
            # Sleep for specified interval
            time.sleep(self.report_interval)

    def start(self):
        """
        Start node client service
        """
        if self.thread and self.thread.is_alive():
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_loop)
        self.thread.daemon = True
        self.thread.start()
        print(f"Node service started: {self.node_name} ({self.node_id})")
        print(f"Using default LLM model: {self.default_llm}")
        
    def stop(self):
        """
        Stop node client service
        """
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        print("Node service stopped")