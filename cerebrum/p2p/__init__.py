"""
Peer-to-peer networking package for AIOS decentralized operations.

This package provides peer-to-peer networking capabilities for decentralized
agent discovery, presence synchronization, and communication.
"""

# Import public modules and subpackages
from . import dht
from . import gossip

__all__ = ['dht', 'gossip']
