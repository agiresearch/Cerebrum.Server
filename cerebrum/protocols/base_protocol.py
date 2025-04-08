"""
Base protocol implementation for AIOS communication.
"""

import uuid
from datetime import datetime
from typing import Dict, Any

class AIOSProtocol:
    """Base communication protocol for AIOS"""
    
    def __init__(self, agent_id: str, node_id: str = None):
        """
        Initialize protocol handler
        
        Args:
            agent_id: Agent identifier
            node_id: Node identifier
        """
        self.agent_id = agent_id
        self.node_id = node_id
        self.capabilities = []
        
    def create_message(self, 
                      recipient_id: str,
                      message_type: str,
                      content: Dict[str, Any],
                      conversation_id: str = None) -> Dict[str, Any]:
        """Create standard protocol message"""
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            
        return {
            "protocol_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "sender": {
                "id": self.agent_id,
                "node_id": self.node_id
            },
            "recipient": {
                "id": recipient_id
            },
            "message_type": message_type,
            "content": content
        } 