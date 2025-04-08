"""
Communication performance testing implementation.
"""

import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
from .base_performance_test import BasePerformanceTest

class CommunicationTester(BasePerformanceTest):
    """Tests communication performance"""
    
    def __init__(self, registry_url: str = "http://localhost:3000"):
        """Initialize communication tester"""
        super().__init__(registry_url)
        self.success_count = 0
        self.total_requests = 0

    def single_request(self) -> bool:
        """Execute single test request"""
        try:
            start_time = time.time()
            
            payload = {
                "type": "custom",
                "data": {
                    "message": "test message",
                    "agent": "example/test_agent"
                }
            }
            
            response = requests.post(
                f"{self.registry_url}/api/nodes/tasks",
                json=payload,
                timeout=5
            )
            
            latency = time.time() - start_time
            
            if response.status_code == 200:
                self.success_count += 1
                self.results.append(latency)
                
            self.total_requests += 1
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Request Error: {e}")
            self.total_requests += 1
            return False

    def run_load_test(self, num_requests: int, concurrent_users: int):
        """Execute load test scenario"""
        print(f"\nStarting Load Test:")
        print(f"Total Requests: {num_requests}")
        print(f"Concurrent Users: {concurrent_users}")
        
        self.start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(self.single_request) 
                      for _ in range(num_requests)]
            
        self.end_time = time.time()
        
        metrics = self.calculate_metrics()
        metrics["success_rate"] = (self.success_count / self.total_requests) * 100
        metrics["throughput"] = self.total_requests / metrics["total_time"]
        
        self.print_extended_results(metrics)

    def print_extended_results(self, metrics: Dict[str, float]):
        """Display detailed test results"""
        super().print_results(metrics, "Communication Load Test")
        print(f"Success Rate: {metrics['success_rate']:.1f}%")
        print(f"Throughput: {metrics['throughput']:.1f} requests/second") 