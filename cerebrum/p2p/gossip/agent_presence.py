"""
Agent presence synchronization using Gossip protocol.

This module provides a service for synchronizing agent availability
information across AIOS nodes using a Gossip-based protocol.
"""

import asyncio
import json
import logging
import socket
import time
import uuid
from typing import Dict, List, Set, Any, Optional, Callable
from .protocol import GossipProtocol, GossipMessage, NodeState

logger = logging.getLogger(__name__)

class AgentPresence:
    """
    Agent presence information.
    """
    
    def __init__(self, agent_id: str, node_id: str, capabilities: List[str] = None,
                last_updated: float = None):
        """
        Initialize agent presence.
        
        Args:
            agent_id: Agent identifier
            node_id: Hosting node identifier
            capabilities: Agent capabilities
            last_updated: Last update timestamp
        """
        self.agent_id = agent_id
        self.node_id = node_id
        self.capabilities = capabilities or []
        self.last_updated = last_updated or time.time()
        self.status = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "node_id": self.node_id,
            "capabilities": self.capabilities,
            "last_updated": self.last_updated,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentPresence':
        """Create from dictionary."""
        return cls(
            data.get("agent_id", ""),
            data.get("node_id", ""),
            data.get("capabilities", []),
            data.get("last_updated", time.time())
        )


class AgentPresenceService:
    """
    Service for propagating and synchronizing agent presence information.
    """
    
    # Message types
    MSG_AGENT_ACTIVE = "agent_active"
    MSG_AGENT_INACTIVE = "agent_inactive"
    MSG_AGENT_QUERY = "agent_query"
    MSG_AGENT_INFO = "agent_info"
    
    def __init__(self, node_id: str = None, host: str = "127.0.0.1", port: int = 8001):
        """
        Initialize agent presence service.
        
        Args:
            node_id: Node identifier (generated if None)
            host: Local host address
            port: Local port
        """
        self.node_id = node_id or str(uuid.uuid4())
        self.host = host
        self.port = port
        self.gossip = None
        self.transport = None
        self.running = False
        
        # Local agent presence information
        self.local_agents: Dict[str, AgentPresence] = {}
        
        # Remote agent presence information
        self.remote_agents: Dict[str, AgentPresence] = {}
        
        # Callbacks for agent presence events
        self.callbacks: Dict[str, List[Callable]] = {
            "agent_active": [],
            "agent_inactive": [],
            "agent_updated": [],
            "agent_discovered": []
        }
    
    async def start(self):
        """Start the agent presence service."""
        if self.running:
            return
            
        loop = asyncio.get_event_loop()
        
        try:
            # Create and set up Gossip protocol
            self.gossip = GossipProtocol(self.node_id, self.port)
            
            # Set up transport
            transport, _ = await loop.create_datagram_endpoint(
                lambda: self.gossip,
                local_addr=(self.host, self.port)
            )
            
            self.transport = transport
            
            # Register message handlers
            self.gossip.register_callback(self.MSG_AGENT_ACTIVE, self._handle_agent_active)
            self.gossip.register_callback(self.MSG_AGENT_INACTIVE, self._handle_agent_inactive)
            self.gossip.register_callback(self.MSG_AGENT_QUERY, self._handle_agent_query)
            self.gossip.register_callback(self.MSG_AGENT_INFO, self._handle_agent_info)
            
            self.running = True
            logger.info(f"Agent Presence Service started on {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start Agent Presence Service: {e}")
            if self.transport:
                self.transport.close()
    
    def stop(self):
        """Stop the agent presence service."""
        if not self.running:
            return
            
        if self.gossip:
            self.gossip.stop_tasks()
            
        if self.transport:
            self.transport.close()
            
        self.running = False
        logger.info("Agent Presence Service stopped")
    
    def register_agent(self, agent_id: str, capabilities: List[str] = None) -> bool:
        """
        Register a local agent.
        
        Args:
            agent_id: Agent identifier
            capabilities: Agent capabilities
            
        Returns:
            Whether registration was successful
        """
        if not self.running:
            logger.error("Cannot register agent, service not running")
            return False
            
        try:
            # Create agent presence
            presence = AgentPresence(agent_id, self.node_id, capabilities)
            
            # Store locally
            self.local_agents[agent_id] = presence
            
            # Propagate to network
            self._propagate_agent_active(presence)
            
            logger.info(f"Registered agent {agent_id} with capabilities: {capabilities}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            return False
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister a local agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Whether unregistration was successful
        """
        if not self.running:
            logger.error("Cannot unregister agent, service not running")
            return False
            
        try:
            if agent_id in self.local_agents:
                # Get presence info
                presence = self.local_agents[agent_id]
                
                # Remove locally
                del self.local_agents[agent_id]
                
                # Propagate to network
                self._propagate_agent_inactive(presence)
                
                logger.info(f"Unregistered agent {agent_id}")
                return True
            else:
                logger.warning(f"Agent {agent_id} not found for unregistration")
                return False
                
        except Exception as e:
            logger.error(f"Error unregistering agent {agent_id}: {e}")
            return False
    
    def update_agent_capabilities(self, agent_id: str, capabilities: List[str]) -> bool:
        """
        Update a local agent's capabilities.
        
        Args:
            agent_id: Agent identifier
            capabilities: Updated capabilities
            
        Returns:
            Whether update was successful
        """
        if not self.running:
            logger.error("Cannot update agent, service not running")
            return False
            
        try:
            if agent_id in self.local_agents:
                # Update presence info
                presence = self.local_agents[agent_id]
                presence.capabilities = capabilities
                presence.last_updated = time.time()
                
                # Propagate to network
                self._propagate_agent_active(presence)
                
                logger.info(f"Updated capabilities for agent {agent_id}")
                return True
            else:
                logger.warning(f"Agent {agent_id} not found for update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            return False
    
    def query_agent(self, agent_id: str) -> Optional[AgentPresence]:
        """
        Query agent presence information.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent presence information or None if not found
        """
        # Check local agents first
        if agent_id in self.local_agents:
            return self.local_agents[agent_id]
            
        # Then check remote agents
        if agent_id in self.remote_agents:
            return self.remote_agents[agent_id]
            
        # Not found, propagate query to network
        if self.running:
            self._propagate_agent_query(agent_id)
            
        return None
    
    def get_local_agents(self) -> Dict[str, AgentPresence]:
        """
        Get all local agents.
        
        Returns:
            Dictionary of agent_id to presence information
        """
        return {agent_id: presence.to_dict() for agent_id, presence in self.local_agents.items()}
    
    def get_remote_agents(self) -> Dict[str, AgentPresence]:
        """
        Get all remote agents.
        
        Returns:
            Dictionary of agent_id to presence information
        """
        return {agent_id: presence.to_dict() for agent_id, presence in self.remote_agents.items()}
    
    def get_all_agents(self) -> Dict[str, AgentPresence]:
        """
        Get all known agents.
        
        Returns:
            Dictionary of agent_id to presence information
        """
        all_agents = self.get_local_agents()
        all_agents.update(self.get_remote_agents())
        return all_agents
    
    def get_agents_by_capability(self, capability: str) -> List[AgentPresence]:
        """
        Get agents with a specific capability.
        
        Args:
            capability: Required capability
            
        Returns:
            List of matching agents
        """
        matching_agents = []
        
        # Check local agents
        for presence in self.local_agents.values():
            if capability in presence.capabilities:
                matching_agents.append(presence)
                
        # Check remote agents
        for presence in self.remote_agents.values():
            if capability in presence.capabilities:
                matching_agents.append(presence)
                
        return matching_agents
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for agent presence events.
        
        Args:
            event_type: Event type (agent_active, agent_inactive, agent_updated, agent_discovered)
            callback: Callback function
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def add_peer(self, peer_id: str, host: str, port: int):
        """
        Add a peer to the Gossip network.
        
        Args:
            peer_id: Peer node ID
            host: Peer host address
            port: Peer port
        """
        if self.gossip:
            self.gossip.add_peer(peer_id, host, port)
            logger.info(f"Added peer {peer_id} at {host}:{port}")
    
    def _propagate_agent_active(self, presence: AgentPresence):
        """
        Propagate agent active message.
        
        Args:
            presence: Agent presence information
        """
        if not self.gossip:
            return
            
        message = GossipMessage(
            self.node_id,
            self.MSG_AGENT_ACTIVE,
            {"presence": presence.to_dict()}
        )
        
        for peer in self.gossip.get_active_peers().values():
            addr = (peer["ip"], peer["port"])
            self.gossip._send_message(message, addr)
    
    def _propagate_agent_inactive(self, presence: AgentPresence):
        """
        Propagate agent inactive message.
        
        Args:
            presence: Agent presence information
        """
        if not self.gossip:
            return
            
        message = GossipMessage(
            self.node_id,
            self.MSG_AGENT_INACTIVE,
            {"agent_id": presence.agent_id, "node_id": presence.node_id}
        )
        
        for peer in self.gossip.get_active_peers().values():
            addr = (peer["ip"], peer["port"])
            self.gossip._send_message(message, addr)
    
    def _propagate_agent_query(self, agent_id: str):
        """
        Propagate agent query message.
        
        Args:
            agent_id: Agent identifier
        """
        if not self.gossip:
            return
            
        message = GossipMessage(
            self.node_id,
            self.MSG_AGENT_QUERY,
            {"agent_id": agent_id, "requester": self.node_id}
        )
        
        for peer in self.gossip.get_active_peers().values():
            addr = (peer["ip"], peer["port"])
            self.gossip._send_message(message, addr)
    
    def _handle_agent_active(self, message: GossipMessage):
        """
        Handle agent active message.
        
        Args:
            message: Received message
        """
        presence_data = message.data.get("presence", {})
        if not presence_data:
            return
            
        presence = AgentPresence.from_dict(presence_data)
        agent_id = presence.agent_id
        
        # Skip if it's our own agent
        if presence.node_id == self.node_id:
            return
            
        is_new = agent_id not in self.remote_agents
        is_updated = False
        
        if not is_new:
            # Check if update is newer
            existing_presence = self.remote_agents[agent_id]
            is_updated = presence.last_updated > existing_presence.last_updated
            
        if is_new or is_updated:
            # Store updated presence
            self.remote_agents[agent_id] = presence
            
            # Trigger callbacks
            if is_new:
                self._trigger_callbacks("agent_discovered", agent_id, presence)
                logger.info(f"Discovered remote agent {agent_id} on node {presence.node_id}")
            else:
                self._trigger_callbacks("agent_updated", agent_id, presence)
                logger.info(f"Updated remote agent {agent_id} on node {presence.node_id}")
    
    def _handle_agent_inactive(self, message: GossipMessage):
        """
        Handle agent inactive message.
        
        Args:
            message: Received message
        """
        agent_id = message.data.get("agent_id")
        node_id = message.data.get("node_id")
        
        if not agent_id or not node_id:
            return
            
        if agent_id in self.remote_agents and self.remote_agents[agent_id].node_id == node_id:
            # Remove agent
            presence = self.remote_agents.pop(agent_id)
            
            # Trigger callbacks
            self._trigger_callbacks("agent_inactive", agent_id, presence)
            logger.info(f"Remote agent {agent_id} on node {node_id} is now inactive")
    
    def _handle_agent_query(self, message: GossipMessage):
        """
        Handle agent query message.
        
        Args:
            message: Received message
        """
        agent_id = message.data.get("agent_id")
        requester = message.data.get("requester")
        
        if not agent_id or not requester or requester == self.node_id:
            return
            
        # Check if we have the agent
        if agent_id in self.local_agents:
            presence = self.local_agents[agent_id]
            self._send_agent_info(presence, requester)
            
        elif agent_id in self.remote_agents:
            presence = self.remote_agents[agent_id]
            self._send_agent_info(presence, requester)
    
    def _handle_agent_info(self, message: GossipMessage):
        """
        Handle agent info message.
        
        Args:
            message: Received message
        """
        presence_data = message.data.get("presence", {})
        target = message.data.get("target")
        
        if not presence_data or target != self.node_id:
            return
            
        presence = AgentPresence.from_dict(presence_data)
        agent_id = presence.agent_id
        
        # Skip if it's our own agent
        if presence.node_id == self.node_id:
            return
            
        # Store presence
        if agent_id not in self.remote_agents:
            self.remote_agents[agent_id] = presence
            
            # Trigger callbacks
            self._trigger_callbacks("agent_discovered", agent_id, presence)
            logger.info(f"Discovered remote agent {agent_id} on node {presence.node_id} from query")
            
        else:
            # Update if newer
            existing_presence = self.remote_agents[agent_id]
            if presence.last_updated > existing_presence.last_updated:
                self.remote_agents[agent_id] = presence
                
                # Trigger callbacks
                self._trigger_callbacks("agent_updated", agent_id, presence)
                logger.info(f"Updated remote agent {agent_id} on node {presence.node_id} from query")
    
    def _send_agent_info(self, presence: AgentPresence, target_node: str):
        """
        Send agent info to a specific node.
        
        Args:
            presence: Agent presence information
            target_node: Target node ID
        """
        if not self.gossip:
            return
            
        # Find target peer
        for peer_id, peer_data in self.gossip.peers.items():
            if peer_id == target_node:
                message = GossipMessage(
                    self.node_id,
                    self.MSG_AGENT_INFO,
                    {"presence": presence.to_dict(), "target": target_node}
                )
                
                addr = (peer_data["ip"], peer_data["port"])
                self.gossip._send_message(message, addr)
                return
    
    def _trigger_callbacks(self, event_type: str, agent_id: str, presence: AgentPresence):
        """
        Trigger callbacks for an event.
        
        Args:
            event_type: Event type
            agent_id: Agent identifier
            presence: Agent presence information
        """
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(agent_id, presence.to_dict())
                except Exception as e:
                    logger.error(f"Error in callback for {event_type}: {e}")


class GossipAgentDirectoryService:
    """
    Service for decentralized agent directory using Gossip protocol.
    """
    
    def __init__(self, node_id: str = None, host: str = "127.0.0.1", port: int = 8001, 
                seed_nodes: List[tuple] = None):
        """
        Initialize service.
        
        Args:
            node_id: Node identifier (generated if None)
            host: Local host address
            port: Local port
            seed_nodes: List of (node_id, host, port) tuples for bootstrap
        """
        self.node_id = node_id or str(uuid.uuid4())
        self.presence_service = AgentPresenceService(self.node_id, host, port)
        self.seed_nodes = seed_nodes or []
        self.running = False
    
    async def start(self):
        """Start the service."""
        if self.running:
            return
            
        # Start presence service
        await self.presence_service.start()
        
        # Connect to seed nodes
        for node_id, host, port in self.seed_nodes:
            self.presence_service.add_peer(node_id, host, port)
        
        self.running = True
        logger.info("Gossip Agent Directory Service started")
    
    def stop(self):
        """Stop the service."""
        if not self.running:
            return
            
        self.presence_service.stop()
        self.running = False
        logger.info("Gossip Agent Directory Service stopped")
    
    def register_agent(self, agent_id: str, capabilities: List[str] = None) -> bool:
        """
        Register an agent.
        
        Args:
            agent_id: Agent identifier
            capabilities: Agent capabilities
            
        Returns:
            Whether registration was successful
        """
        return self.presence_service.register_agent(agent_id, capabilities)
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Whether unregistration was successful
        """
        return self.presence_service.unregister_agent(agent_id)
    
    def update_agent(self, agent_id: str, capabilities: List[str]) -> bool:
        """
        Update an agent.
        
        Args:
            agent_id: Agent identifier
            capabilities: Updated capabilities
            
        Returns:
            Whether update was successful
        """
        return self.presence_service.update_agent_capabilities(agent_id, capabilities)
    
    def query_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Query agent information.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent information or None if not found
        """
        presence = self.presence_service.query_agent(agent_id)
        return presence.to_dict() if presence else None
    
    def find_agents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Find agents with a specific capability.
        
        Args:
            capability: Required capability
            
        Returns:
            List of matching agents
        """
        agents = self.presence_service.get_agents_by_capability(capability)
        return [a.to_dict() for a in agents]
    
    def list_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        List all known agents.
        
        Returns:
            Dictionary of agent_id to agent information
        """
        return self.presence_service.get_all_agents()
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for agent events.
        
        Args:
            event_type: Event type
            callback: Callback function
        """
        self.presence_service.register_callback(event_type, callback)
    
    def add_peer(self, node_id: str, host: str, port: int):
        """
        Add a peer node.
        
        Args:
            node_id: Node identifier
            host: Node host address
            port: Node port
        """
        self.presence_service.add_peer(node_id, host, port) 