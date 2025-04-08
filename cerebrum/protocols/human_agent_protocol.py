"""
Protocol implementation for human-agent communication.
Extends base protocol with human-specific message handling.
"""

from typing import Dict, Any
from .base_protocol import AIOSProtocol

class HumanAgentProtocol(AIOSProtocol):
    """
    Protocol handler for human-agent interactions
    """
    
    def create_human_message(self,
                           agent_id: str,
                           task: str,
                           parameters: Dict[str, Any] = None,
                           conversation_id: str = None) -> Dict[str, Any]:
        """
        Generate human-to-agent message
        
        Args:
            agent_id: Target agent identifier
            task: Task description
            parameters: Optional task parameters
            conversation_id: Optional conversation thread ID
            
        Returns:
            Formatted human-to-agent message
        """
        content = {
            "task": task
        }
        
        if parameters:
            content["parameters"] = parameters
            
        message = self.create_message(
            recipient_id=agent_id,
            message_type="request",
            content=content,
            conversation_id=conversation_id
        )
        
        message["sender"]["type"] = "human"
        message["recipient"]["type"] = "agent"
        
        return message
    
    def create_agent_response(self,
                            human_id: str,
                            result: Any,
                            status: str = "success",
                            conversation_id: str = None) -> Dict[str, Any]:
        """
        Generate agent-to-human response
        
        Args:
            human_id: Human recipient identifier
            result: Task outcome/response
            status: Task status indicator
            conversation_id: Conversation thread ID
            
        Returns:
            Formatted agent-to-human message
        """
        content = {
            "result": result,
            "status": status
        }
        
        message = self.create_message(
            recipient_id=human_id,
            message_type="response",
            content=content,
            conversation_id=conversation_id
        )
        
        message["sender"]["type"] = "agent"
        message["recipient"]["type"] = "human"
        
        return message 