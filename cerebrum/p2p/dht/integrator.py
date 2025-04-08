"""
DHT integration with AIOS.

This module provides the integration layer between the DHT implementation
and the AIOS system, offering agent registration and discovery.
"""

import asyncio
import logging
import socket
import time
from typing import Dict, Any, List, Optional, Set, Callable
from .node import DHT, NodeID
from .protocol import DHTProtocol, DHTClient

logger = logging.getLogger(__name__)

class AgentDirectory:
    """
    Agent directory using DHT for decentralized registration.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9000, 
                bootstrap_nodes: List[tuple] = None):
        """
        Initialize agent directory.
        
        Args:
            host: Local host address
            port: Local port
            bootstrap_nodes: List of (host, port) tuples for bootstrap
        """
        self.host = host
        self.port = port
        self.dht = DHT(host, port)
        self.protocol = None
        self.client = None
        self.bootstrap_nodes = bootstrap_nodes or []
        self.running = False
        self.loop = None
        self.transport = None
        
        # Local cache of registered agents
        self.local_agents: Dict[str, Dict[str, Any]] = {}
        
        # Agent event callbacks
        self.agent_callbacks: Dict[str, List[Callable]] = {
            "registered": [],
            "updated": [],
            "discovered": []
        }
        
    async def start(self):
        """Start the DHT service."""
        if self.running:
            return
            
        self.loop = asyncio.get_event_loop()
        
        try:
            # Create and bind protocol
            transport, protocol = await self.loop.create_datagram_endpoint(
                lambda: DHTProtocol(self.dht),
                local_addr=(self.host, self.port)
            )
            
            self.transport = transport
            self.protocol = protocol
            self.client = DHTClient(protocol)
            
            # Bootstrap DHT
            if self.bootstrap_nodes:
                await self._bootstrap()
                
            self.running = True
            logger.info(f"DHT service started on {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start DHT service: {e}")
            if self.transport:
                self.transport.close()
    
    def stop(self):
        """Stop the DHT service."""
        if not self.running:
            return
            
        if self.transport:
            self.transport.close()
            
        self.running = False
        logger.info("DHT service stopped")
    
    async def _bootstrap(self):
        """Bootstrap DHT by connecting to known nodes."""
        logger.info(f"Bootstrapping DHT with {len(self.bootstrap_nodes)} nodes")
        
        for host, port in self.bootstrap_nodes:
            try:
                # Create a temporary node for the bootstrap node
                bootstrap_id = NodeID.from_string(f"{host}:{port}")
                bootstrap_node = self.dht.local_node.__class__(bootstrap_id, host, port)
                
                # Ping the bootstrap node
                is_alive = await self.client.ping(bootstrap_node)
                
                if is_alive:
                    logger.info(f"Connected to bootstrap node {host}:{port}")
                    
                    # Find nodes close to ourselves to populate routing table
                    closest_nodes = await self.client.find_node(
                        self.dht.node_id, bootstrap_node)
                    
                    logger.info(f"Discovered {len(closest_nodes)} nodes from bootstrap")
                    
            except Exception as e:
                logger.error(f"Error bootstrapping with {host}:{port}: {e}")
    
    async def register_agent(self, agent_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Register an agent in the DHT.
        
        Args:
            agent_id: Unique agent identifier
            metadata: Agent metadata including capabilities
            
        Returns:
            Whether registration was successful
        """
        if not self.running:
            logger.error("Cannot register agent, DHT service not running")
            return False
            
        try:
            # Add registration time
            metadata["registered_at"] = time.time()
            metadata["last_updated"] = time.time()
            
            # Store in local cache
            self.local_agents[agent_id] = metadata
            
            # Store in DHT
            success = self.dht.register_agent(agent_id, metadata)
            
            if success:
                logger.info(f"Agent {agent_id} registered locally")
                
                # Trigger callbacks
                for callback in self.agent_callbacks.get("registered", []):
                    try:
                        callback(agent_id, metadata)
                    except Exception as e:
                        logger.error(f"Error in agent registration callback: {e}")
                
                # Replicate to other nodes
                await self._replicate_agent_registration(agent_id, metadata)
                
            return success
            
        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            return False
    
    async def update_agent(self, agent_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update an agent's metadata in the DHT.
        
        Args:
            agent_id: Agent identifier
            metadata: Updated metadata
            
        Returns:
            Whether update was successful
        """
        if not self.running:
            logger.error("Cannot update agent, DHT service not running")
            return False
            
        try:
            # Update timestamp
            metadata["last_updated"] = time.time()
            
            # Preserve registration time if exists
            if agent_id in self.local_agents and "registered_at" in self.local_agents[agent_id]:
                metadata["registered_at"] = self.local_agents[agent_id]["registered_at"]
            
            # Update local cache
            self.local_agents[agent_id] = metadata
            
            # Update in DHT
            success = self.dht.register_agent(agent_id, metadata)
            
            if success:
                logger.info(f"Agent {agent_id} updated locally")
                
                # Trigger callbacks
                for callback in self.agent_callbacks.get("updated", []):
                    try:
                        callback(agent_id, metadata)
                    except Exception as e:
                        logger.error(f"Error in agent update callback: {e}")
                
                # Replicate to other nodes
                await self._replicate_agent_registration(agent_id, metadata)
                
            return success
            
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            return False
    
    async def find_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Find an agent in the DHT.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent metadata or None if not found
        """
        if not self.running:
            logger.error("Cannot find agent, DHT service not running")
            return None
            
        try:
            # Check local cache first
            if agent_id in self.local_agents:
                return self.local_agents[agent_id]
                
            # Check local DHT store
            local_result = self.dht.find_agent(agent_id)
            if local_result:
                # Cache result
                self.local_agents[agent_id] = local_result
                
                # Trigger callbacks
                for callback in self.agent_callbacks.get("discovered", []):
                    try:
                        callback(agent_id, local_result)
                    except Exception as e:
                        logger.error(f"Error in agent discovery callback: {e}")
                
                return local_result
                
            # Agent not found locally, search in DHT network
            return await self._search_agent_in_network(agent_id)
            
        except Exception as e:
            logger.error(f"Error finding agent {agent_id}: {e}")
            return None
    
    async def _search_agent_in_network(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Search for an agent in the DHT network.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent metadata or None if not found
        """
        if not self.client:
            return None
            
        key = f"agent:{agent_id}"
        key_id = NodeID.from_string(key)
        
        # Get closest nodes to the key
        closest_nodes = self.dht.routing_table.get_closest_nodes(key_id, 3)
        
        for node in closest_nodes:
            try:
                value, _ = await self.client.find_value(key, node)
                if value:
                    # Cache result
                    self.local_agents[agent_id] = value
                    
                    # Trigger callbacks
                    for callback in self.agent_callbacks.get("discovered", []):
                        try:
                            callback(agent_id, value)
                        except Exception as e:
                            logger.error(f"Error in agent discovery callback: {e}")
                    
                    return value
            except Exception as e:
                logger.error(f"Error querying node {node.ip}:{node.port} for agent {agent_id}: {e}")
        
        return None
    
    async def _replicate_agent_registration(self, agent_id: str, metadata: Dict[str, Any]):
        """
        Replicate agent registration to other nodes.
        
        Args:
            agent_id: Agent identifier
            metadata: Agent metadata
        """
        if not self.client:
            return
            
        key = f"agent:{agent_id}"
        key_id = NodeID.from_string(key)
        
        # Get closest nodes to the key
        closest_nodes = self.dht.routing_table.get_closest_nodes(key_id, 3)
        
        for node in closest_nodes:
            try:
                # Skip if node is ourselves
                if (node.ip == self.host and node.port == self.port) or \
                   node.node_id == self.dht.node_id:
                    continue
                    
                # Store at remote node
                success = await self.client.store(key, metadata, node)
                if success:
                    logger.info(f"Replicated agent {agent_id} to node {node.ip}:{node.port}")
                
            except Exception as e:
                logger.error(f"Error replicating agent {agent_id} to node {node.ip}:{node.port}: {e}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for agent events.
        
        Args:
            event_type: Event type (registered, updated, discovered)
            callback: Callback function
        """
        if event_type in self.agent_callbacks:
            self.agent_callbacks[event_type].append(callback)
    
    def list_local_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of locally known agents.
        
        Returns:
            Dictionary of agent_id to metadata
        """
        return self.local_agents.copy()


class DHTAgentRegistryService:
    """
    Service wrapper for DHT-based agent registry.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9000,
                bootstrap_nodes: List[tuple] = None):
        """
        Initialize service.
        
        Args:
            host: Local host address
            port: Local port
            bootstrap_nodes: List of (host, port) tuples for bootstrap
        """
        self.directory = AgentDirectory(host, port, bootstrap_nodes)
        self.running = False
        self.task = None
    
    async def start(self):
        """Start the service."""
        if self.running:
            return
            
        await self.directory.start()
        self.running = True
        logger.info("DHT Agent Registry Service started")
    
    async def stop(self):
        """Stop the service."""
        if not self.running:
            return
            
        self.directory.stop()
        self.running = False
        logger.info("DHT Agent Registry Service stopped")
    
    async def register_agent(self, agent_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Register an agent.
        
        Args:
            agent_id: Agent identifier
            metadata: Agent metadata
            
        Returns:
            Whether registration was successful
        """
        return await self.directory.register_agent(agent_id, metadata)
    
    async def update_agent(self, agent_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update an agent.
        
        Args:
            agent_id: Agent identifier
            metadata: Updated metadata
            
        Returns:
            Whether update was successful
        """
        return await self.directory.update_agent(agent_id, metadata)
    
    async def find_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Find an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent metadata or None if not found
        """
        return await self.directory.find_agent(agent_id)
    
    def list_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        List known agents.
        
        Returns:
            Dictionary of agent_id to metadata
        """
        return self.directory.list_local_agents()
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for agent events.
        
        Args:
            event_type: Event type (registered, updated, discovered)
            callback: Callback function
        """
        self.directory.register_callback(event_type, callback) 