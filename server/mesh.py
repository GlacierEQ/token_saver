import hashlib
import bisect
import urllib.request
import urllib.error
import json
from typing import List, Optional, Any, Dict

from server.discovery import PeerRegistry
from token_saver_elite_core import EliteMemoryCache

class HashRing:
    """Consistent hashing ring for distributed cache routing."""
    def __init__(self, replicas: int = 150):
        self.replicas = replicas
        self.ring: Dict[int, str] = {}
        self.sorted_keys: List[int] = []

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16)

    def add_node(self, node_id: str) -> None:
        """Add a node to the hash ring."""
        for i in range(self.replicas):
            key = self._hash(f"{node_id}:{i}")
            self.ring[key] = node_id
            bisect.insort(self.sorted_keys, key)

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the hash ring."""
        for i in range(self.replicas):
            key = self._hash(f"{node_id}:{i}")
            if key in self.ring:
                del self.ring[key]
                self.sorted_keys.remove(key)

    def get_node(self, key: str) -> Optional[str]:
        """Get the primary responsible node for a key."""
        if not self.ring:
            return None
        h = self._hash(key)
        idx = bisect.bisect(self.sorted_keys, h)
        if idx == len(self.sorted_keys):
            idx = 0
        return self.ring[self.sorted_keys[idx]]

    def get_nodes(self, key: str, count: int = 3) -> List[str]:
        """Get the top N responsible nodes for a key (for replication)."""
        if not self.ring:
            return []
        
        nodes = []
        h = self._hash(key)
        idx = bisect.bisect(self.sorted_keys, h)
        
        for _ in range(len(self.sorted_keys)):
            if idx == len(self.sorted_keys):
                idx = 0
            node = self.ring[self.sorted_keys[idx]]
            if node not in nodes:
                nodes.append(node)
                if len(nodes) == count:
                    break
            idx += 1
            
        return nodes

class DistributedCache:
    """Wraps local cache and handles distributed routing."""
    def __init__(self, local_id: str, cache: EliteMemoryCache, registry: PeerRegistry):
        self.local_id = local_id
        self.cache = cache
        self.registry = registry
        self.ring = HashRing()
        self.ring.add_node(local_id)

    def _update_ring(self) -> None:
        active_peers = self.registry.get_active_peers()
        current_nodes = set(self.ring.ring.values())
        
        expected_nodes = {self.local_id} | {peer.id for peer in active_peers}
        
        for node in current_nodes - expected_nodes:
            self.ring.remove_node(node)
            
        for node in expected_nodes - current_nodes:
            self.ring.add_node(node)

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache, forwarding to responsible node if necessary."""
        self._update_ring()
        nodes = self.ring.get_nodes(key, count=1)
        if not nodes:
            return self.cache.get(key)
            
        primary = nodes[0]
        if primary == self.local_id:
            return self.cache.get(key)
            
        try:
            req = urllib.request.Request(f"http://{primary}/cache/{key}")
            with urllib.request.urlopen(req, timeout=1.0) as response:
                if response.status == 200:
                    data = json.loads(response.read())
                    return data.get("value")
        except Exception:
            pass
            
        return self.cache.get(key)

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set a value in the cache, replicating to backup nodes."""
        self._update_ring()
        nodes = self.ring.get_nodes(key, count=3)
        
        for node in nodes:
            if node == self.local_id:
                self.cache.set(key, value, ttl=ttl)
            else:
                try:
                    data = json.dumps({"key": key, "value": value, "ttl": ttl}).encode("utf-8")
                    req = urllib.request.Request(
                        f"http://{node}/cache",
                        data=data,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    urllib.request.urlopen(req, timeout=1.0)
                except Exception:
                    pass
        
        if self.local_id not in nodes:
            self.cache.set(key, value, ttl=ttl)
