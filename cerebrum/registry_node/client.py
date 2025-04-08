"""
Registry node client core implementation.
"""

from cerebrum.node.base_client import BaseNodeClient  # 更新为新的引用路径

class RegistryNodeClient(BaseNodeClient):
    """
    Registry-specific node client implementation
    """
    
    def __init__(self, registry_url: str, node_name: str = None, report_interval: int = 30, default_llm: str = "gpt-4o-mini"):
        """
        Initialize registry node client
        """
        super().__init__(registry_url, node_name, report_interval, default_llm)
        self._registry_specific_setup()
    
    def _registry_specific_setup(self):
        """
        Perform registry-specific initialization
        """
        # Add registry-specific setup here
        pass 