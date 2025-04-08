"""
Registry node client entry point.
"""

import sys
from cerebrum.registry_node import run_registry_node

def main():
    """Entry point for the run-registry-node command."""
    return run_registry_node()

if __name__ == "__main__":
    sys.exit(main()) 