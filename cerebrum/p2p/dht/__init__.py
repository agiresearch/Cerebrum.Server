"""
Distributed Hash Table (DHT) package for AIOS decentralized discovery.

This package provides DHT-based discovery and registration capabilities
for decentralized agent and service discovery.
"""

# Import public modules and classes
from .integrator import AgentDirectory, DHTAgentRegistryService

__all__ = ['AgentDirectory', 'DHTAgentRegistryService']
