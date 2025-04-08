"""
Base performance testing implementation.
"""

import time
import statistics
from typing import Dict, Any, List
from datetime import datetime

class BasePerformanceTest:
    """Base class for performance testing"""
    
    def __init__(self, registry_url: str = "http://localhost:3000"):
        """Initialize performance tester"""
        self.registry_url = registry_url
        self.results: List[float] = []
        self.start_time: float = 0
        self.end_time: float = 0

    def calculate_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics"""
        if not self.results:
            return {
                "average": 0.0,
                "maximum": 0.0,
                "minimum": 0.0,
                "total_time": 0.0
            }

        return {
            "average": statistics.mean(self.results),
            "maximum": max(self.results),
            "minimum": min(self.results),
            "total_time": self.end_time - self.start_time
        }

    def print_results(self, metrics: Dict[str, float], test_name: str):
        """Display test results"""
        print(f"\nPerformance Test Results - {test_name}")
        print("-" * 50)
        print(f"Average Response Time: {metrics['average']:.3f} seconds")
        print(f"Maximum Response Time: {metrics['maximum']:.3f} seconds")
        print(f"Minimum Response Time: {metrics['minimum']:.3f} seconds")
        print(f"Total Test Duration: {metrics['total_time']:.3f} seconds") 