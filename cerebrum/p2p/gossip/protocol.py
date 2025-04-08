"""
Gossip protocol implementation.

This module provides a Gossip protocol implementation for presence synchronization,
allowing nodes to exchange state information in a decentralized manner.
"""

import asyncio
import json
import logging
import random
import socket
import time
from typing import Dict, List, Set, Any, Callable, Optional, Tuple

logger = logging.getLogger(__name__)

# Default protocol parameters
DEFAULT_GOSSIP_INTERVAL = 5.0  # seconds
DEFAULT_CLEANUP_INTERVAL = 30.0  # seconds
DEFAULT_SUSPICION_TIMEOUT = 10.0  # seconds
DEFAULT_DEAD_TIMEOUT = 60.0  # seconds
DEFAULT_MAX_TRANSMIT_COUNT = 3


class NodeState:
    """
    States for nodes in the Gossip network.
    """
    ALIVE = "alive"
    SUSPECT = "suspect"
    DEAD = "dead"


class GossipMessage:
    """
    Message format for Gossip protocol communications.
    """
    
    def __init__(self, sender_id: str, message_type: str, data: Dict[str, Any],
                timestamp: float = None, ttl: int = DEFAULT_MAX_TRANSMIT_COUNT):
        """
        Initialize a Gossip message.
        
        Args:
            sender_id: Sender node ID
            message_type: Message type
            data: Message data
            timestamp: Message timestamp
            ttl: Time-to-live (number of hops)
        """
        self.sender_id = sender_id
        self.message_type = message_type
        self.data = data
        self.timestamp = timestamp or time.time()
        self.ttl = ttl
        self.message_id = f"{sender_id}:{self.timestamp}:{hash(str(data))}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "sender_id": self.sender_id,
            "type": self.message_type,
            "data": self.data,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GossipMessage':
        """Create message from dictionary."""
        return cls(
            data.get("sender_id", ""),
            data.get("type", ""),
            data.get("data", {}),
            data.get("timestamp", time.time()),
            data.get("ttl", DEFAULT_MAX_TRANSMIT_COUNT)
        )
    
    def encode(self) -> bytes:
        """Encode message as bytes."""
        return json.dumps(self.to_dict()).encode('utf-8')
    
    @classmethod
    def decode(cls, data: bytes) -> 'GossipMessage':
        """Decode message from bytes."""
        try:
            dict_data = json.loads(data.decode('utf-8'))
            return cls.from_dict(dict_data)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode Gossip message: {data}")
            return cls("unknown", "error", {"error": "Invalid message format"})


class GossipProtocol(asyncio.DatagramProtocol):
    """
    UDP protocol implementation for Gossip communication.
    """
    
    def __init__(self, node_id: str, port: int = 8001):
        """
        Initialize Gossip protocol.
        
        Args:
            node_id: Local node ID
            port: Local UDP port
        """
        self.node_id = node_id
        self.port = port
        self.transport = None
        
        # The set of peers we know about
        self.peers: Dict[str, Dict[str, Any]] = {}
        
        # Keep track of processed messages to avoid duplicates
        self.message_cache: Dict[str, float] = {}
        
        # Callbacks for message types
        self.callbacks: Dict[str, List[Callable]] = {}
        
        # Gossip and cleanup tasks
        self.gossip_task = None
        self.cleanup_task = None
        
        # Message types
        self.MSG_PING = "ping"
        self.MSG_ACK = "ack"
        self.MSG_SYNC = "sync"
        self.MSG_STATE = "state"
        self.MSG_SUSPECT = "suspect"
        self.MSG_DEAD = "dead"
        
        # Configure intervals
        self.gossip_interval = DEFAULT_GOSSIP_INTERVAL
        self.cleanup_interval = DEFAULT_CLEANUP_INTERVAL
        self.suspicion_timeout = DEFAULT_SUSPICION_TIMEOUT
        self.dead_timeout = DEFAULT_DEAD_TIMEOUT
    
    def connection_made(self, transport):
        """Called when connection is established."""
        self.transport = transport
        self.start_tasks()
    
    def datagram_received(self, data, addr):
        """
        Handle received datagram.
        
        Args:
            data: Received bytes
            addr: Sender address (ip, port)
        """
        try:
            message = GossipMessage.decode(data)
            if self._should_process_message(message):
                self._process_message(message, addr)
        except Exception as e:
            logger.error(f"Error processing Gossip message: {e}")
    
    def _should_process_message(self, message: GossipMessage) -> bool:
        """
        Check if message should be processed.
        
        Args:
            message: Received message
            
        Returns:
            Whether message should be processed
        """
        # Skip messages from ourselves
        if message.sender_id == self.node_id:
            return False
            
        # Check if message was already processed
        if message.message_id in self.message_cache:
            return False
            
        # Check TTL
        if message.ttl <= 0:
            return False
            
        # Add to message cache
        self.message_cache[message.message_id] = time.time()
        
        return True
    
    def _process_message(self, message: GossipMessage, addr: Tuple[str, int]):
        """
        Process received message.
        
        Args:
            message: Received message
            addr: Sender address
        """
        # Update peer info
        self._update_peer(message.sender_id, addr[0], addr[1], NodeState.ALIVE)
        
        # Handle specific message types
        if message.message_type == self.MSG_PING:
            self._handle_ping(message, addr)
        elif message.message_type == self.MSG_ACK:
            self._handle_ack(message)
        elif message.message_type == self.MSG_SYNC:
            self._handle_sync(message, addr)
        elif message.message_type == self.MSG_STATE:
            self._handle_state(message)
        elif message.message_type == self.MSG_SUSPECT:
            self._handle_suspect(message)
        elif message.message_type == self.MSG_DEAD:
            self._handle_dead(message)
            
        # Trigger callbacks
        self._trigger_callbacks(message)
        
        # Propagate message
        self._propagate_message(message)
    
    def _update_peer(self, peer_id: str, ip: str, port: int, state: str = NodeState.ALIVE):
        """
        Update peer information.
        
        Args:
            peer_id: Peer node ID
            ip: Peer IP address
            port: Peer port
            state: Peer state
        """
        if peer_id == self.node_id:
            return  # Don't track ourselves
            
        if peer_id in self.peers:
            # Update existing peer
            self.peers[peer_id]["last_seen"] = time.time()
            
            # Only update state if it's more recent
            if state == NodeState.DEAD or \
               (state == NodeState.SUSPECT and self.peers[peer_id]["state"] == NodeState.ALIVE):
                self.peers[peer_id]["state"] = state
                
            # Update address if needed
            if self.peers[peer_id]["ip"] != ip or self.peers[peer_id]["port"] != port:
                self.peers[peer_id]["ip"] = ip
                self.peers[peer_id]["port"] = port
        else:
            # New peer
            self.peers[peer_id] = {
                "ip": ip,
                "port": port,
                "state": state,
                "last_seen": time.time(),
                "incarnation": 0
            }
            logger.info(f"New peer discovered: {peer_id} at {ip}:{port}")
    
    def _send_message(self, message: GossipMessage, addr: Tuple[str, int]):
        """
        Send a message.
        
        Args:
            message: Message to send
            addr: Destination address
        """
        if self.transport:
            try:
                self.transport.sendto(message.encode(), addr)
            except Exception as e:
                logger.error(f"Error sending message to {addr}: {e}")
        else:
            logger.error("Cannot send message, transport not available")
    
    def _propagate_message(self, message: GossipMessage):
        """
        Propagate a message to other peers.
        
        Args:
            message: Message to propagate
        """
        # Decrement TTL
        if message.ttl <= 1:
            return
            
        # Create new message with decremented TTL
        new_message = GossipMessage(
            message.sender_id,
            message.message_type,
            message.data,
            message.timestamp,
            message.ttl - 1
        )
        
        # Select random subset of peers to propagate to
        live_peers = [p for p in self.peers.values() 
                     if p["state"] != NodeState.DEAD]
                     
        if not live_peers:
            return
            
        # Select up to sqrt(n) peers to gossip to
        target_count = min(len(live_peers), max(3, int(len(live_peers) ** 0.5)))
        targets = random.sample(live_peers, target_count)
        
        for peer in targets:
            addr = (peer["ip"], peer["port"])
            self._send_message(new_message, addr)
    
    def _handle_ping(self, message: GossipMessage, addr: Tuple[str, int]):
        """Handle ping message by sending ACK."""
        ack = GossipMessage(
            self.node_id,
            self.MSG_ACK,
            {"target": message.sender_id}
        )
        self._send_message(ack, addr)
    
    def _handle_ack(self, message: GossipMessage):
        """Handle acknowledgement message."""
        # Reset suspicion state if this is a response to our probe
        target = message.data.get("target")
        if target == self.node_id and message.sender_id in self.peers:
            if self.peers[message.sender_id]["state"] == NodeState.SUSPECT:
                self.peers[message.sender_id]["state"] = NodeState.ALIVE
                logger.info(f"Peer {message.sender_id} is alive again")
    
    def _handle_sync(self, message: GossipMessage, addr: Tuple[str, int]):
        """Handle synchronization request."""
        # Send our current state
        state_msg = GossipMessage(
            self.node_id,
            self.MSG_STATE,
            {"peers": self._get_peers_state()}
        )
        self._send_message(state_msg, addr)
    
    def _handle_state(self, message: GossipMessage):
        """Handle state update message."""
        remote_peers = message.data.get("peers", {})
        
        for peer_id, peer_data in remote_peers.items():
            if peer_id == self.node_id:
                continue  # Skip ourselves
                
            if peer_id in self.peers:
                # Existing peer
                if peer_data.get("incarnation", 0) > self.peers[peer_id].get("incarnation", 0):
                    # Update with newer state
                    self.peers[peer_id].update(peer_data)
                    logger.debug(f"Updated peer {peer_id} state from sync")
            else:
                # New peer
                if "ip" in peer_data and "port" in peer_data:
                    self.peers[peer_id] = peer_data
                    self.peers[peer_id]["last_seen"] = time.time()
                    logger.info(f"Added new peer {peer_id} from sync")
    
    def _handle_suspect(self, message: GossipMessage):
        """Handle suspect node message."""
        suspect_id = message.data.get("peer_id")
        if not suspect_id or suspect_id == self.node_id:
            return
            
        if suspect_id in self.peers:
            # Mark as suspect if not already dead
            if self.peers[suspect_id]["state"] != NodeState.DEAD:
                self.peers[suspect_id]["state"] = NodeState.SUSPECT
                self.peers[suspect_id]["suspect_time"] = time.time()
                logger.info(f"Peer {suspect_id} is suspected to be down")
    
    def _handle_dead(self, message: GossipMessage):
        """Handle dead node message."""
        dead_id = message.data.get("peer_id")
        if not dead_id or dead_id == self.node_id:
            return
            
        if dead_id in self.peers:
            # Mark as dead
            self.peers[dead_id]["state"] = NodeState.DEAD
            logger.info(f"Peer {dead_id} is confirmed dead")
    
    def _get_peers_state(self) -> Dict[str, Dict[str, Any]]:
        """
        Get state of all peers for synchronization.
        
        Returns:
            Dictionary of peer states
        """
        peers_copy = {}
        for peer_id, peer_data in self.peers.items():
            peers_copy[peer_id] = peer_data.copy()
        return peers_copy
    
    def _trigger_callbacks(self, message: GossipMessage):
        """
        Trigger callbacks for a message.
        
        Args:
            message: Message that triggered callbacks
        """
        if message.message_type in self.callbacks:
            for callback in self.callbacks[message.message_type]:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in callback for {message.message_type}: {e}")
    
    def register_callback(self, message_type: str, callback: Callable):
        """
        Register a callback for a message type.
        
        Args:
            message_type: Message type
            callback: Callback function
        """
        if message_type not in self.callbacks:
            self.callbacks[message_type] = []
        self.callbacks[message_type].append(callback)
    
    def add_peer(self, peer_id: str, ip: str, port: int):
        """
        Add a peer to the known peers.
        
        Args:
            peer_id: Peer node ID
            ip: Peer IP address
            port: Peer port
        """
        self._update_peer(peer_id, ip, port)
    
    def start_tasks(self):
        """Start periodic tasks."""
        loop = asyncio.get_event_loop()
        self.gossip_task = loop.create_task(self._gossip_task())
        self.cleanup_task = loop.create_task(self._cleanup_task())
    
    def stop_tasks(self):
        """Stop periodic tasks."""
        if self.gossip_task:
            self.gossip_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
    
    async def _gossip_task(self):
        """Periodic task to gossip with peers."""
        while True:
            try:
                await self._gossip()
                await asyncio.sleep(self.gossip_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in gossip task: {e}")
                await asyncio.sleep(self.gossip_interval)
    
    async def _cleanup_task(self):
        """Periodic task to clean up peer list."""
        while True:
            try:
                self._check_peers()
                self._clean_message_cache()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(self.cleanup_interval)
    
    async def _gossip(self):
        """Perform gossip with random peers."""
        # Get list of alive peers
        live_peers = [p for p in self.peers.values() 
                     if p["state"] != NodeState.DEAD]
        
        if not live_peers:
            return
            
        # Select random peer to sync with
        peer = random.choice(live_peers)
        
        # Send sync message
        sync_msg = GossipMessage(
            self.node_id,
            self.MSG_SYNC,
            {}
        )
        
        addr = (peer["ip"], peer["port"])
        self._send_message(sync_msg, addr)
    
    def _check_peers(self):
        """Check peer status and mark suspected/dead nodes."""
        now = time.time()
        
        for peer_id, peer in list(self.peers.items()):
            if peer["state"] == NodeState.DEAD:
                # Clean up dead peers after timeout
                if now - peer["last_seen"] > self.dead_timeout:
                    del self.peers[peer_id]
                    logger.info(f"Removed dead peer {peer_id}")
                continue
                
            if peer["state"] == NodeState.SUSPECT:
                # Check if suspicion timeout has elapsed
                if "suspect_time" in peer and now - peer["suspect_time"] > self.suspicion_timeout:
                    # Mark as dead
                    peer["state"] = NodeState.DEAD
                    logger.info(f"Peer {peer_id} timed out, marked as dead")
                    
                    # Propagate dead message
                    dead_msg = GossipMessage(
                        self.node_id,
                        self.MSG_DEAD,
                        {"peer_id": peer_id}
                    )
                    
                    self._propagate_to_all(dead_msg)
                    
            elif peer["state"] == NodeState.ALIVE:
                # Check if no recent contact
                if now - peer["last_seen"] > self.suspicion_timeout:
                    # Mark as suspect
                    peer["state"] = NodeState.SUSPECT
                    peer["suspect_time"] = now
                    logger.info(f"No recent contact with {peer_id}, marking as suspect")
                    
                    # Send direct ping
                    ping_msg = GossipMessage(
                        self.node_id,
                        self.MSG_PING,
                        {}
                    )
                    
                    addr = (peer["ip"], peer["port"])
                    self._send_message(ping_msg, addr)
                    
                    # Propagate suspect message
                    suspect_msg = GossipMessage(
                        self.node_id,
                        self.MSG_SUSPECT,
                        {"peer_id": peer_id}
                    )
                    
                    self._propagate_to_all(suspect_msg)
    
    def _clean_message_cache(self):
        """Clean up old messages from cache."""
        now = time.time()
        expired = []
        
        for msg_id, timestamp in self.message_cache.items():
            if now - timestamp > self.cleanup_interval * 2:
                expired.append(msg_id)
                
        for msg_id in expired:
            del self.message_cache[msg_id]
    
    def _propagate_to_all(self, message: GossipMessage):
        """
        Propagate a message to all live peers.
        
        Args:
            message: Message to propagate
        """
        for peer in self.peers.values():
            if peer["state"] != NodeState.DEAD:
                addr = (peer["ip"], peer["port"])
                self._send_message(message, addr)
    
    
    def get_active_peers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of active peers.
        
        Returns:
            Dictionary of active peers
        """
        return {pid: pdata for pid, pdata in self.peers.items() 
                if pdata["state"] != NodeState.DEAD}
    
    def get_peer(self, peer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific peer.
        
        Args:
            peer_id: Peer node ID
            
        Returns:
            Peer data or None if not found
        """
        return self.peers.get(peer_id) 