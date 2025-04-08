"""
Distributed Hash Table (DHT) node implementation.

This module provides a Kademlia-inspired DHT implementation for AIOS,
enabling decentralized agent registration and discovery.
"""

import hashlib
import random
import time
from typing import Dict, List, Tuple, Optional, Any, Set, Callable
import threading
import logging

logger = logging.getLogger(__name__)

class NodeID:
    """
    Represents a unique identifier for a node in the DHT.
    """
    
    def __init__(self, id_bytes: bytes = None):
        """
        Initialize a node ID.
        
        Args:
            id_bytes: Optional bytes to use as ID. If None, random ID is generated.
        """
        if id_bytes is None:
            # Generate a random 160-bit ID (20 bytes)
            self.id_bytes = random.getrandbits(160).to_bytes(20, byteorder='big')
        else:
            self.id_bytes = id_bytes
    
    @classmethod
    def from_string(cls, string_value: str) -> 'NodeID':
        """
        Create a NodeID from a string by hashing it.
        
        Args:
            string_value: String to hash
            
        Returns:
            NodeID instance
        """
        hash_bytes = hashlib.sha1(string_value.encode('utf-8')).digest()
        return cls(hash_bytes)
    
    def distance(self, other: 'NodeID') -> int:
        """
        Calculate XOR distance between two node IDs.
        
        Args:
            other: Other NodeID
            
        Returns:
            XOR distance as int
        """
        # XOR the bytes of the two IDs
        xor_result = bytes(a ^ b for a, b in zip(self.id_bytes, other.id_bytes))
        # Convert to integer for distance comparison
        return int.from_bytes(xor_result, byteorder='big')
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NodeID):
            return False
        return self.id_bytes == other.id_bytes
    
    def __hash__(self) -> int:
        return hash(self.id_bytes)
    
    def __str__(self) -> str:
        return self.id_bytes.hex()


class Node:
    """
    Represents a contact (node) in the DHT network.
    """
    
    def __init__(self, node_id: NodeID, ip: str, port: int):
        """
        Initialize a node.
        
        Args:
            node_id: Unique identifier
            ip: IP address
            port: Port number
        """
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.last_seen = time.time()
    
    def update_last_seen(self):
        """Update the last_seen timestamp."""
        self.last_seen = time.time()
    
    def is_active(self, stale_threshold: int = 3600) -> bool:
        """
        Check if node is considered active.
        
        Args:
            stale_threshold: Seconds after which a node is considered inactive
            
        Returns:
            Whether node is active
        """
        return (time.time() - self.last_seen) < stale_threshold
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return False
        return (self.node_id == other.node_id and 
                self.ip == other.ip and 
                self.port == other.port)
    
    def __hash__(self) -> int:
        return hash((self.node_id, self.ip, self.port))


class KBucket:
    """
    K-bucket for storing nodes in DHT routing table.
    """
    
    def __init__(self, k: int = 20):
        """
        Initialize a k-bucket.
        
        Args:
            k: Maximum number of nodes in bucket
        """
        self.nodes: List[Node] = []
        self.k = k
    
    def add_node(self, node: Node) -> bool:
        """
        Add a node to the bucket.
        
        Args:
            node: Node to add
            
        Returns:
            Whether node was added
        """
        # If node already exists, move it to the end (most recently seen)
        for i, existing_node in enumerate(self.nodes):
            if existing_node.node_id == node.node_id:
                self.nodes.pop(i)
                self.nodes.append(node)
                return True
        
        # If bucket not full, add node
        if len(self.nodes) < self.k:
            self.nodes.append(node)
            return True
            
        # Bucket full, can't add
        return False
    
    def get_nodes(self) -> List[Node]:
        """Get list of nodes in bucket."""
        return self.nodes.copy()


class RoutingTable:
    """
    DHT routing table for storing contact information of other nodes.
    """
    
    def __init__(self, local_node_id: NodeID, k: int = 20, bits: int = 160):
        """
        Initialize routing table.
        
        Args:
            local_node_id: ID of the local node
            k: Maximum size of k-buckets
            bits: Number of bits in node ID
        """
        self.local_node_id = local_node_id
        self.k = k
        self.bits = bits
        self.buckets = [KBucket(k) for _ in range(bits)]
    
    def add_node(self, node: Node) -> bool:
        """
        Add a node to the routing table.
        
        Args:
            node: Node to add
            
        Returns:
            Whether node was added
        """
        if node.node_id == self.local_node_id:
            return False  # Don't add ourselves
            
        bucket_index = self._get_bucket_index(node.node_id)
        return self.buckets[bucket_index].add_node(node)
    
    def get_closest_nodes(self, target_id: NodeID, count: int) -> List[Node]:
        """
        Get nodes closest to a target ID.
        
        Args:
            target_id: Target node ID
            count: Maximum number of nodes to return
            
        Returns:
            List of closest nodes
        """
        # Start with bucket that would contain the target, then adjacent buckets
        nodes = []
        bucket_index = self._get_bucket_index(target_id)
        
        # Add nodes from target bucket
        nodes.extend(self.buckets[bucket_index].get_nodes())
        
        # Add nodes from adjacent buckets if needed
        left_bucket = bucket_index - 1
        right_bucket = bucket_index + 1
        
        while len(nodes) < count and (left_bucket >= 0 or right_bucket < self.bits):
            if left_bucket >= 0:
                nodes.extend(self.buckets[left_bucket].get_nodes())
                left_bucket -= 1
                
            if right_bucket < self.bits:
                nodes.extend(self.buckets[right_bucket].get_nodes())
                right_bucket += 1
        
        # Sort by distance to target
        nodes.sort(key=lambda node: target_id.distance(node.node_id))
        
        return nodes[:count]
    
    def _get_bucket_index(self, node_id: NodeID) -> int:
        """
        Determine which bucket a node belongs in.
        
        Args:
            node_id: Node ID
            
        Returns:
            Bucket index
        """
        distance = self.local_node_id.distance(node_id)
        if distance == 0:
            return 0
            
        # Calculate the position of the highest bit set (distance to node)
        return self.bits - (distance.bit_length())


class DHT:
    """
    Distributed Hash Table implementation.
    """
    
    def __init__(self, ip: str, port: int, node_id: NodeID = None, k: int = 20):
        """
        Initialize DHT node.
        
        Args:
            ip: Local IP address
            port: Local port
            node_id: Node ID (generated if None)
            k: DHT replication parameter (k-bucket size)
        """
        self.node_id = node_id or NodeID()
        self.ip = ip
        self.port = port
        
        # Create local node
        self.local_node = Node(self.node_id, ip, port)
        
        # Initialize routing table
        self.routing_table = RoutingTable(self.node_id, k)
        
        # Storage for DHT data
        self.data_store: Dict[str, Any] = {}
        
        # Registered callbacks
        self.callbacks: Dict[str, List[Callable]] = {}
        
    def bootstrap(self, seeds: List[Tuple[str, int]]):
        """
        Bootstrap the DHT by connecting to seed nodes.
        
        Args:
            seeds: List of (ip, port) tuples for seed nodes
        """
        for ip, port in seeds:
            # In a real implementation, this would:
            # 1. Contact the seed node
            # 2. Perform node lookup for our own ID
            # 3. Refresh buckets
            pass
            
    def store(self, key: str, value: Any) -> bool:
        """
        Store a key-value pair in the DHT.
        
        Args:
            key: Storage key
            value: Value to store
            
        Returns:
            Whether storage was successful
        """
        # In a real implementation, this would:
        # 1. Find k closest nodes to the key
        # 2. Send STORE commands to those nodes
        
        # For now, just store locally
        self.data_store[key] = value
        return True
            
    def lookup(self, key: str) -> Optional[Any]:
        """
        Lookup a value in the DHT.
        
        Args:
            key: Lookup key
            
        Returns:
            Retrieved value or None
        """
        # In a real implementation, this would:
        # 1. Find k closest nodes to the key
        # 2. Send FIND_VALUE commands to those nodes
        
        # For now, just lookup locally
        return self.data_store.get(key)
            
    def register_agent(self, agent_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Register an agent in the DHT.
        
        Args:
            agent_id: Unique agent identifier
            metadata: Agent metadata (capabilities, etc.)
            
        Returns:
            Whether registration was successful
        """
        key = f"agent:{agent_id}"
        metadata["last_update"] = time.time()
        metadata["node_id"] = str(self.node_id)
        metadata["node_ip"] = self.ip
        metadata["node_port"] = self.port
        
        return self.store(key, metadata)
            
    def find_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Find an agent in the DHT.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent metadata or None
        """
        key = f"agent:{agent_id}"
        return self.lookup(key)
            
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for DHT events.
        
        Args:
            event_type: Event type
            callback: Callback function
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
            
        self.callbacks[event_type].append(callback)
            
    def trigger_callbacks(self, event_type: str, data: Any):
        """
        Trigger callbacks for an event.
        
        Args:
            event_type: Event type
            data: Event data
        """
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in callback: {e}") 