"""
Node discovery performance testing implementation.
"""

from typing import List, Dict, Any
import time
from cerebrum.node import BaseNodeClient
from .base_performance_test import BasePerformanceTest

class NodeDiscoveryTester(BasePerformanceTest):
    """Tests node discovery performance"""
    
    def __init__(self, registry_url: str = "http://localhost:3000"):
        """Initialize node discovery tester"""
        super().__init__(registry_url)
        self.nodes: List[BaseNodeClient] = []

    def start_node(self, node_index: int) -> BaseNodeClient:
        """Start and register test node"""
        try:
            start_time = time.time()
            
            node = BaseNodeClient(
                registry_url=self.registry_url,
                node_name=f"test_node_{node_index}",
                report_interval=5
            )
            
            node.set_available_agents(["example/test_agent"])
            node.start()
            
            registration_time = time.time() - start_time
            self.results.append(registration_time)
            
            self.nodes.append(node)
            print(f"Node {node_index} registered in {registration_time:.3f} seconds")
            
            return node
            
        except Exception as e:
            print(f"Node startup error: {e}")
            return None

    def run_discovery_test(self, num_nodes: int):
        """Execute node discovery test"""
        print(f"\nStarting Node Discovery Test (Nodes: {num_nodes})")
        
        self.start_time = time.time()
        
        for i in range(num_nodes):
            self.start_node(i)
            time.sleep(1)  # Stagger node startup
            
        self.end_time = time.time()
        
        metrics = self.calculate_metrics()
        self.print_results(metrics, "Node Discovery Test")

    def cleanup(self):
        """Clean up test nodes"""
        for node in self.nodes:
            try:
                node.stop()
            except Exception as e:
                print(f"Cleanup error: {e}")
        print("Test nodes cleaned up") 