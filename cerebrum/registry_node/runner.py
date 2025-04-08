"""
Registry node client runner implementation.
"""

import signal
import sys
import time
from .client import RegistryNodeClient
from .utils import parse_arguments, setup_signal_handlers

def run_registry_node():
    """
    Main entry point for running registry node client
    """
    args = parse_arguments()
    
    available_agents = []
    if args.agents:
        available_agents = [agent.strip() for agent in args.agents.split(',')]
    
    client = RegistryNodeClient(
        registry_url=args.registry_url,
        node_name=args.node_name,
        report_interval=args.report_interval,
        default_llm=args.default_llm
    )
    
    setup_signal_handlers(client)
    
    try:
        print(f"Starting Registry Node Client...")
        print(f"Registry URL: {args.registry_url}")
        print(f"Default LLM: {args.default_llm}")
        if args.default_llm == "gemini-1.5-flash":
            print("Using Google Gemini model, ensure Google API key is configured")
        print(f"Available agents: {', '.join(available_agents) if available_agents else 'None'}")
        
        client.set_available_agents(available_agents)
        client.start()
        
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