"""
DHT protocol implementation.

This module provides a network protocol implementation for DHT communication,
handling message encoding/decoding and network operations.
"""

import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from .node import NodeID, Node, DHT

logger = logging.getLogger(__name__)

# Message types
MSG_PING = "ping"
MSG_PONG = "pong"
MSG_FIND_NODE = "find_node"
MSG_FIND_VALUE = "find_value"
MSG_STORE = "store"
MSG_FOUND_NODES = "found_nodes"
MSG_FOUND_VALUE = "found_value"


class Message:
    """
    DHT protocol message.
    """
    
    def __init__(self, msg_type: str, sender_id: str, data: Dict[str, Any], message_id: str = None):
        """
        Initialize a DHT message.
        
        Args:
            msg_type: Message type
            sender_id: Sender node ID
            data: Message data
            message_id: Optional message ID
        """
        self.msg_type = msg_type
        self.sender_id = sender_id
        self.data = data
        self.message_id = message_id or str(hash(str(data) + str(sender_id)))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "type": self.msg_type,
            "sender": self.sender_id,
            "data": self.data,
            "id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        return cls(
            data.get("type", "unknown"),
            data.get("sender", ""),
            data.get("data", {}),
            data.get("id")
        )
    
    def encode(self) -> bytes:
        """Encode message as bytes."""
        return json.dumps(self.to_dict()).encode('utf-8')
    
    @classmethod
    def decode(cls, data: bytes) -> 'Message':
        """Decode message from bytes."""
        try:
            dict_data = json.loads(data.decode('utf-8'))
            return cls.from_dict(dict_data)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode message: {data}")
            return cls("error", "", {"error": "Invalid message format"})


class DHTProtocol(asyncio.DatagramProtocol):
    """
    UDP protocol implementation for DHT communication.
    """
    
    def __init__(self, dht: DHT):
        """
        Initialize DHT protocol.
        
        Args:
            dht: DHT instance
        """
        self.dht = dht
        self.transport = None
        self.handlers = {
            MSG_PING: self._handle_ping,
            MSG_FIND_NODE: self._handle_find_node,
            MSG_FIND_VALUE: self._handle_find_value,
            MSG_STORE: self._handle_store,
            MSG_PONG: self._handle_pong,
            MSG_FOUND_NODES: self._handle_found_nodes,
            MSG_FOUND_VALUE: self._handle_found_value
        }
        # Pending requests waiting for responses
        self.pending_requests: Dict[str, asyncio.Future] = {}
    
    def connection_made(self, transport):
        """Called when connection is established."""
        self.transport = transport
    
    def datagram_received(self, data, addr):
        """
        Handle received datagram.
        
        Args:
            data: Received bytes
            addr: Sender address (ip, port)
        """
        try:
            message = Message.decode(data)
            self._process_message(message, addr)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _process_message(self, message: Message, addr: Tuple[str, int]):
        """
        Process received message.
        
        Args:
            message: Received message
            addr: Sender address
        """
        if message.msg_type in self.handlers:
            sender_node_id = NodeID.from_string(message.sender_id)
            sender_node = Node(sender_node_id, addr[0], addr[1])
            
            # Update routing table with sender
            self.dht.routing_table.add_node(sender_node)
            
            # Handle message
            self.handlers[message.msg_type](message, addr)
        else:
            logger.warning(f"Unknown message type: {message.msg_type}")
    
    def _send_message(self, message: Message, addr: Tuple[str, int]):
        """
        Send a message.
        
        Args:
            message: Message to send
            addr: Destination address
        """
        if self.transport:
            self.transport.sendto(message.encode(), addr)
        else:
            logger.error("Cannot send message, transport not available")
    
    async def send_request(self, msg_type: str, data: Dict[str, Any], 
                         addr: Tuple[str, int], timeout: float = 5.0) -> Optional[Message]:
        """
        Send a request and wait for response.
        
        Args:
            msg_type: Message type
            data: Message data
            addr: Destination address
            timeout: Timeout in seconds
            
        Returns:
            Response message or None on timeout
        """
        # Create request message
        message = Message(msg_type, str(self.dht.node_id), data)
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[message.message_id] = future
        
        # Send message
        self._send_message(message, addr)
        
        try:
            # Wait for response with timeout
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Request timed out: {msg_type} to {addr}")
            return None
        finally:
            # Clean up pending request
            self.pending_requests.pop(message.message_id, None)
    
    def _resolve_pending_request(self, message_id: str, response: Message):
        """
        Resolve a pending request.
        
        Args:
            message_id: Request message ID
            response: Response message
        """
        if message_id in self.pending_requests:
            future = self.pending_requests[message_id]
            if not future.done():
                future.set_result(response)
    
    # Message handlers
    
    def _handle_ping(self, message: Message, addr: Tuple[str, int]):
        """Handle ping message."""
        pong = Message(MSG_PONG, str(self.dht.node_id), 
                      {"request_id": message.message_id})
        self._send_message(pong, addr)
    
    def _handle_pong(self, message: Message, addr: Tuple[str, int]):
        """Handle pong message."""
        request_id = message.data.get("request_id")
        if request_id:
            self._resolve_pending_request(request_id, message)
    
    def _handle_find_node(self, message: Message, addr: Tuple[str, int]):
        """Handle find_node message."""
        target_id_str = message.data.get("target_id")
        if not target_id_str:
            return
            
        target_id = NodeID.from_string(target_id_str)
        nodes = self.dht.routing_table.get_closest_nodes(target_id, 20)
        
        # Format nodes for response
        node_list = [
            {"id": str(node.node_id), "ip": node.ip, "port": node.port}
            for node in nodes
        ]
        
        response = Message(MSG_FOUND_NODES, str(self.dht.node_id), {
            "request_id": message.message_id,
            "nodes": node_list
        })
        
        self._send_message(response, addr)
    
    def _handle_found_nodes(self, message: Message, addr: Tuple[str, int]):
        """Handle found_nodes message."""
        request_id = message.data.get("request_id")
        if request_id:
            self._resolve_pending_request(request_id, message)
    
    def _handle_find_value(self, message: Message, addr: Tuple[str, int]):
        """Handle find_value message."""
        key = message.data.get("key")
        if not key:
            return
            
        value = self.dht.data_store.get(key)
        
        if value is not None:
            # Found value, return it
            response = Message(MSG_FOUND_VALUE, str(self.dht.node_id), {
                "request_id": message.message_id,
                "key": key,
                "value": value
            })
        else:
            # Value not found, return closest nodes
            target_id = NodeID.from_string(key)
            nodes = self.dht.routing_table.get_closest_nodes(target_id, 20)
            
            node_list = [
                {"id": str(node.node_id), "ip": node.ip, "port": node.port}
                for node in nodes
            ]
            
            response = Message(MSG_FOUND_NODES, str(self.dht.node_id), {
                "request_id": message.message_id,
                "key": key,
                "nodes": node_list
            })
        
        self._send_message(response, addr)
    
    def _handle_found_value(self, message: Message, addr: Tuple[str, int]):
        """Handle found_value message."""
        request_id = message.data.get("request_id")
        if request_id:
            self._resolve_pending_request(request_id, message)
    
    def _handle_store(self, message: Message, addr: Tuple[str, int]):
        """Handle store message."""
        key = message.data.get("key")
        value = message.data.get("value")
        
        if key and value is not None:
            self.dht.data_store[key] = value
            
            # Send acknowledgment
            response = Message(MSG_PONG, str(self.dht.node_id), {
                "request_id": message.message_id,
                "status": "success"
            })
            
            self._send_message(response, addr)


class DHTClient:
    """
    High-level DHT client for performing DHT operations.
    """
    
    def __init__(self, protocol: DHTProtocol):
        """
        Initialize DHT client.
        
        Args:
            protocol: DHT protocol instance
        """
        self.protocol = protocol
        self.dht = protocol.dht
    
    async def ping(self, node: Node) -> bool:
        """
        Ping a node.
        
        Args:
            node: Target node
            
        Returns:
            Whether node responded
        """
        response = await self.protocol.send_request(
            MSG_PING, {}, (node.ip, node.port))
        return response is not None
    
    async def find_node(self, target_id: NodeID, node: Node) -> List[Node]:
        """
        Find nodes closest to a target ID.
        
        Args:
            target_id: Target node ID
            node: Node to query
            
        Returns:
            List of found nodes
        """
        response = await self.protocol.send_request(
            MSG_FIND_NODE, 
            {"target_id": str(target_id)}, 
            (node.ip, node.port)
        )
        
        if response and response.msg_type == MSG_FOUND_NODES:
            nodes = []
            for node_data in response.data.get("nodes", []):
                node_id = NodeID.from_string(node_data.get("id", ""))
                node = Node(node_id, node_data.get("ip", ""), node_data.get("port", 0))
                nodes.append(node)
                # Update routing table
                self.dht.routing_table.add_node(node)
            return nodes
        
        return []
    
    async def find_value(self, key: str, node: Node) -> Tuple[Optional[Any], List[Node]]:
        """
        Find a value in the DHT.
        
        Args:
            key: Lookup key
            node: Node to query
            
        Returns:
            Tuple of (value, nodes) where value is None if not found
        """
        response = await self.protocol.send_request(
            MSG_FIND_VALUE, 
            {"key": key}, 
            (node.ip, node.port)
        )
        
        if response:
            if response.msg_type == MSG_FOUND_VALUE:
                return response.data.get("value"), []
            elif response.msg_type == MSG_FOUND_NODES:
                nodes = []
                for node_data in response.data.get("nodes", []):
                    node_id = NodeID.from_string(node_data.get("id", ""))
                    node = Node(node_id, node_data.get("ip", ""), node_data.get("port", 0))
                    nodes.append(node)
                    # Update routing table
                    self.dht.routing_table.add_node(node)
                return None, nodes
        
        return None, []
    
    async def store(self, key: str, value: Any, node: Node) -> bool:
        """
        Store a value in the DHT.
        
        Args:
            key: Storage key
            value: Value to store
            node: Node to store at
            
        Returns:
            Whether storage was successful
        """
        response = await self.protocol.send_request(
            MSG_STORE, 
            {"key": key, "value": value}, 
            (node.ip, node.port)
        )
        
        if response and response.msg_type == MSG_PONG:
            return response.data.get("status") == "success"
        
        return False 