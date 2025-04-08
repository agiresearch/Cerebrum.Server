"""
System monitoring and metrics collection implementation.
"""

import psutil
import platform
import socket
import requests
from typing import Dict, Any

class SystemMonitor:
    """
    Monitors system resources and collects metrics
    """
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Collect current system metrics
        
        Returns:
            Dictionary containing system status information
        """
        try:
            return {
                "cpu_percent": self._get_cpu_usage(),
                "memory_percent": self._get_memory_usage(),
                "platform": platform.system(),
                "version": platform.version(),
                "ip_address": self._get_ip_address(),
                "disk_usage": self._get_disk_usage(),
                "network_stats": self._get_network_stats()
            }
        except Exception as e:
            print(f"Error collecting system info: {e}")
            return self._get_fallback_info()

    def _get_cpu_usage(self) -> float:
        """
        Get CPU usage percentage
        """
        return psutil.cpu_percent(interval=1)

    def _get_memory_usage(self) -> float:
        """
        Get memory usage percentage
        """
        return psutil.virtual_memory().percent

    def _get_disk_usage(self) -> Dict[str, float]:
        """
        Get disk usage statistics
        """
        try:
            disk = psutil.disk_usage('/')
            return {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }
        except:
            return {}

    def _get_network_stats(self) -> Dict[str, int]:
        """
        Get network usage statistics
        """
        try:
            stats = psutil.net_io_counters()
            return {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv
            }
        except:
            return {}

    def _get_ip_address(self) -> str:
        """
        Get node IP address
        """
        try:
            response = requests.get('https://api.ipify.org', timeout=3)
            if response.status_code == 200:
                return response.text
            return self._get_local_ip()
        except:
            return self._get_local_ip()

    def _get_local_ip(self) -> str:
        """
        Get local network IP address
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def _get_fallback_info(self) -> Dict[str, Any]:
        """
        Get fallback system information when metrics collection fails
        """
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "platform": platform.system(),
            "version": "Unknown",
            "ip_address": "127.0.0.1",
            "disk_usage": {},
            "network_stats": {}
        } 