"""
Registry node client utilities.
"""

import argparse
import signal
import sys
from typing import Any

def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(description="Run AIOS Registry Node Client")
    
    parser.add_argument(
        "--registry_url",
        type=str,
        default="http://localhost:3000",
        help="AgentHub registry service URL"
    )
    
    parser.add_argument(
        "--node_name",
        type=str,
        default=None,
        help="Node name (defaults to hostname)"
    )
    
    parser.add_argument(
        "--report_interval",
        type=int,
        default=30,
        help="Status report interval (seconds)"
    )
    
    parser.add_argument(
        "--agents",
        type=str,
        default="example/academic_agent",
        help="List of agents available on this node, comma separated"
    )
    
    parser.add_argument(
        "--default_llm",
        type=str,
        default="gpt-4o-mini",
        help="Default LLM model to use (gpt-4o-mini, gemini-1.5-flash, etc.)"
    )
    
    return parser.parse_args()

def setup_signal_handlers(client: Any):
    """
    Set up termination signal handlers
    """
    def handle_signal(sig, frame):
        print("Stopping registry node client...")
        client.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal) 