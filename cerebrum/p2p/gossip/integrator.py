"""
Integration module for connecting Gossip-based presence services to AIOS core.

This module provides integration classes and functions to connect the Gossip-based
agent presence and discovery services into the AIOS ecosystem.
"""

import asyncio
import logging
import os
import json
from typing import Dict, List, Optional, Any, Callable

from cerebrum.config import Config
from cerebrum.core.service import Service
from .agent_presence import GossipAgentDirectoryService

logger = logging.getLogger(__name__)

class GossipIntegrator:
    """
    Integrates Gossip-based agent presence and discovery with AIOS core.
    """
    
    def __init__(self, config: Config = None):
        """
        Initialize Gossip integrator.
        
        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.service = None
        self.node_id = self.config.get("p2p.node_id", default=None)
        self.host = self.config.get("p2p.gossip.host", default="127.0.0.1")
        self.port = self.config.get("p2p.gossip.port", default=8001)
        
        # Parse seed nodes from config
        seed_nodes_str = self.config.get("p2p.gossip.seed_nodes", default="[]")
        try:
            seed_nodes_raw = json.loads(seed_nodes_str)
            self.seed_nodes = []
            for node in seed_nodes_raw:
                if isinstance(node, dict) and 'node_id' in node and 'host' in node and 'port' in node:
                    self.seed_nodes.append((node['node_id'], node['host'], node['port']))
                elif isinstance(node, list) and len(node) == 3:
                    self.seed_nodes.append(tuple(node))
        except Exception as e:
            logger.error(f"Error parsing seed nodes: {e}")
            self.seed_nodes = []
    
    async def initialize(self):
        """Initialize Gossip integrator components."""
        logger.info("Initializing Gossip integrator")
        
        try:
            # Create directory service
            self.service = GossipAgentDirectoryService(
                node_id=self.node_id,
                host=self.host,
                port=self.port,
                seed_nodes=self.seed_nodes
            )
            
            # Start service
            await self.service.start()
            
            logger.info("Gossip integrator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gossip integrator: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown Gossip integrator components."""
        logger.info("Shutting down Gossip integrator")
        
        try:
            if self.service:
                self.service.stop()
            
            logger.info("Gossip integrator shut down successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error shutting down Gossip integrator: {e}")
            return False
    
    def register_agent(self, agent_id: str, capabilities: List[str] = None) -> bool:
        """
        Register an agent with the Gossip network.
        
        Args:
            agent_id: Agent identifier
            capabilities: Agent capabilities
            
        Returns:
            Whether registration was successful
        """
        if not self.service:
            logger.error("Cannot register agent, service not initialized")
            return False
            
        return self.service.register_agent(agent_id, capabilities)
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the Gossip network.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Whether unregistration was successful
        """
        if not self.service:
            logger.error("Cannot unregister agent, service not initialized")
            return False
            
        return self.service.unregister_agent(agent_id)
    
    def update_agent(self, agent_id: str, capabilities: List[str]) -> bool:
        """
        Update an agent's capabilities in the Gossip network.
        
        Args:
            agent_id: Agent identifier
            capabilities: Updated capabilities
            
        Returns:
            Whether update was successful
        """
        if not self.service:
            logger.error("Cannot update agent, service not initialized")
            return False
            
        return self.service.update_agent(agent_id, capabilities)
    
    def query_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Query agent information from the Gossip network.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent information or None if not found
        """
        if not self.service:
            logger.error("Cannot query agent, service not initialized")
            return None
            
        return self.service.query_agent(agent_id)
    
    def find_agents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Find agents with a specific capability in the Gossip network.
        
        Args:
            capability: Required capability
            
        Returns:
            List of matching agents
        """
        if not self.service:
            logger.error("Cannot find agents, service not initialized")
            return []
            
        return self.service.find_agents_by_capability(capability)
    
    def list_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        List all known agents in the Gossip network.
        
        Returns:
            Dictionary of agent_id to agent information
        """
        if not self.service:
            logger.error("Cannot list agents, service not initialized")
            return {}
            
        return self.service.list_agents()
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for agent events.
        
        Args:
            event_type: Event type (agent_active, agent_inactive, agent_updated, agent_discovered)
            callback: Callback function
        """
        if not self.service:
            logger.error("Cannot register callback, service not initialized")
            return
            
        self.service.register_callback(event_type, callback)
    
    def add_peer(self, node_id: str, host: str, port: int):
        """
        Add a peer node to the Gossip network.
        
        Args:
            node_id: Node identifier
            host: Node host address
            port: Node port
        """
        if not self.service:
            logger.error("Cannot add peer, service not initialized")
            return
            
        self.service.add_peer(node_id, host, port)


class GossipPresenceService(Service):
    """
    Service wrapper for Gossip-based agent presence and discovery.
    """
    
    def __init__(self, config: Config = None):
        """
        Initialize service.
        
        Args:
            config: Configuration object
        """
        super().__init__("gossip_presence", config)
        self.integrator = GossipIntegrator(config)
        self.agent_events = []
    
    async def start(self):
        """Start the service."""
        logger.info("Starting Gossip Presence Service")
        
        await self.integrator.initialize()
        
        # Register event handlers
        self.integrator.register_callback("agent_discovered", self._on_agent_discovered)
        self.integrator.register_callback("agent_updated", self._on_agent_updated)
        self.integrator.register_callback("agent_inactive", self._on_agent_inactive)
        
        logger.info("Gossip Presence Service started")
    
    async def stop(self):
        """Stop the service."""
        logger.info("Stopping Gossip Presence Service")
        
        await self.integrator.shutdown()
        
        logger.info("Gossip Presence Service stopped")
    
    def register_agent(self, agent_id: str, capabilities: List[str] = None) -> bool:
        """
        Register an agent.
        
        Args:
            agent_id: Agent identifier
            capabilities: Agent capabilities
            
        Returns:
            Whether registration was successful
        """
        return self.integrator.register_agent(agent_id, capabilities)
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Whether unregistration was successful
        """
        return self.integrator.unregister_agent(agent_id)
    
    def update_agent(self, agent_id: str, capabilities: List[str]) -> bool:
        """
        Update an agent.
        
        Args:
            agent_id: Agent identifier
            capabilities: Updated capabilities
            
        Returns:
            Whether update was successful
        """
        return self.integrator.update_agent(agent_id, capabilities)
    
    def query_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Query agent information.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent information or None if not found
        """
        return self.integrator.query_agent(agent_id)
    
    def find_agents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Find agents with a specific capability.
        
        Args:
            capability: Required capability
            
        Returns:
            List of matching agents
        """
        return self.integrator.find_agents_by_capability(capability)
    
    def list_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        List all known agents.
        
        Returns:
            Dictionary of agent_id to agent information
        """
        return self.integrator.list_agents()
    
    def register_agent_event_handler(self, handler: Callable):
        """
        Register a handler for agent events.
        
        Args:
            handler: Handler function
        """
        self.agent_events.append(handler)
    
    def _on_agent_discovered(self, agent_id: str, presence: Dict[str, Any]):
        """
        Handle agent discovered event.
        
        Args:
            agent_id: Agent identifier
            presence: Agent presence information
        """
        logger.info(f"Discovered remote agent: {agent_id}")
        event = {
            "type": "agent_discovered",
            "agent_id": agent_id,
            "presence": presence
        }
        self._notify_event_handlers(event)
    
    def _on_agent_updated(self, agent_id: str, presence: Dict[str, Any]):
        """
        Handle agent updated event.
        
        Args:
            agent_id: Agent identifier
            presence: Agent presence information
        """
        logger.info(f"Updated remote agent: {agent_id}")
        event = {
            "type": "agent_updated",
            "agent_id": agent_id,
            "presence": presence
        }
        self._notify_event_handlers(event)
    
    def _on_agent_inactive(self, agent_id: str, presence: Dict[str, Any]):
        """
        Handle agent inactive event.
        
        Args:
            agent_id: Agent identifier
            presence: Agent presence information
        """
        logger.info(f"Remote agent inactive: {agent_id}")
        event = {
            "type": "agent_inactive",
            "agent_id": agent_id,
            "presence": presence
        }
        self._notify_event_handlers(event)
    
    def _notify_event_handlers(self, event: Dict[str, Any]):
        """
        Notify all event handlers.
        
        Args:
            event: Event information
        """
        for handler in self.agent_events:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in agent event handler: {e}") 