"""
Gossip protocol package for decentralized agent presence synchronization.

This package provides implementation of the Gossip protocol for
maintaining agent presence and state information across a distributed
AIOS system.
"""

from .protocol import GossipProtocol, GossipMessage, NodeState
from .agent_presence import AgentPresence, AgentPresenceService, GossipAgentDirectoryService
from .integrator import GossipIntegrator, GossipPresenceService

__all__ = [
    'GossipProtocol',
    'GossipMessage',
    'NodeState',
    'AgentPresence',
    'AgentPresenceService',
    'GossipAgentDirectoryService',
    'GossipIntegrator',
    'GossipPresenceService'
]
