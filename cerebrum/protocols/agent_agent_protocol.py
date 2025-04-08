"""
Agent-to-Agent communication protocol implementation.
"""

import requests
from typing import Dict, Any, List, Optional
from .base_protocol import AIOSProtocol

class AgentAgentProtocol(AIOSProtocol):
    """Protocol for Agent-Agent communication"""
    
    def __init__(self, agent_id: str, node_id: str = None):
        """Initialize with agent capabilities"""
        super().__init__(agent_id, node_id)
        self.capabilities = ["text_processing"]
    
    def set_capabilities(self, capabilities: List[str]):
        """Update agent capabilities"""
        self.capabilities = capabilities
    
    def create_agent_message(self,
                           recipient_agent_id: str,
                           recipient_node_id: str,
                           intent: str,
                           task: str,
                           parameters: Dict[str, Any] = None,
                           conversation_id: str = None) -> Dict[str, Any]:
        """Create agent to agent message"""
        content = {
            "task": task
        }
        
        if parameters:
            content["parameters"] = parameters
            
        message = self.create_message(
            recipient_id=recipient_agent_id,
            message_type="request",
            content=content,
            conversation_id=conversation_id
        )
        
        message["sender"]["type"] = "agent"
        message["sender"]["capabilities"] = self.capabilities
        message["recipient"]["type"] = "agent"
        message["recipient"]["node_id"] = recipient_node_id
        message["intent"] = intent
        message["routing"] = {
            "path": [self.node_id],
            "max_hops": 3
        }
        
        return message 