"""
Registry node client runner implementation.
"""

import signal
import sys
import time
from typing import List
from .client import RegistryNodeClient
from .utils import parse_arguments, setup_signal_handlers

def run_registry_node():
    """
    Main entry point for running registry node client
    """
    args = parse_arguments()
    
    # Parse available agents
    available_agents = []
    if args.agents:
        available_agents = [agent.strip() for agent in args.agents.split(',')]
    
    # Create client instance
    client = RegistryNodeClient(
        registry_url=args.registry_url,
        node_name=args.node_name,
        report_interval=args.report_interval
    )
    
    # Set up signal handlers
    setup_signal_handlers(client)
    
    try:
        # Start the client
        print(f"Starting Registry Node Client...")
        print(f"Registry URL: {args.registry_url}")
        print(f"Available agents: {', '.join(available_agents) if available_agents else 'None'}")
        
        client.set_available_agents(available_agents)
        client.start()
        
        # Keep the main thread running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Termination signal received, stopping...")
        client.stop()
    except Exception as e:
        print(f"Error running registry node client: {e}")
        client.stop()
        return 1
        
    return 0 