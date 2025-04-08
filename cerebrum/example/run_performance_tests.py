"""
Performance test runner implementation.
"""

from cerebrum.tests.performance.communication_test import CommunicationTester
from cerebrum.tests.performance.node_discovery_test import NodeDiscoveryTester
import time

def main():
    """Execute performance test suite"""
    # Communication load testing
    comm_tester = CommunicationTester()
    
    test_scenarios = [
        (50, 5),    # Light load
        (100, 10),  # Medium load
        (200, 20)   # Heavy load
    ]
    
    print("Starting Communication Performance Tests")
    print("=" * 50)
    
    for num_requests, concurrent_users in test_scenarios:
        comm_tester.run_load_test(num_requests, concurrent_users)
        time.sleep(2)  # Cool-down period
    
    # Node discovery testing
    node_tester = NodeDiscoveryTester()
    
    print("\nStarting Node Discovery Tests")
    print("=" * 50)
    
    for num_nodes in [3, 5, 7]:
        try:
            node_tester.run_discovery_test(num_nodes)
            time.sleep(5)  # Cool-down period
            node_tester.cleanup()
            time.sleep(2)  # Cleanup interval
        except KeyboardInterrupt:
            print("\nTests interrupted")
            node_tester.cleanup()
            break

if __name__ == "__main__":
    main() 