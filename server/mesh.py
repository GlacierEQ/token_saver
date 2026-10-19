import hashlib
import ipaddress
from urllib.parse import quote
import bisect
import urllib.request
import urllib.error
import json
from typing import List, Optional, Any, Dict

from server.discovery import PeerRegistry
from token_saver_elite_core import EliteMemoryCache


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _safe_peer_url(node_id: str, key: str | None = None) -> str:
    """Construct HTTP URL from the discovered IPv4 peer, never arbitrary URI text."""
    host, sep, port_s = node_id.rpartition(":")
    if not sep or not port_s.isascii() or not port_s.isdecimal():
        raise ValueError("INVALID_PEER_ENDPOINT")
    try:
        ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError as exc:
        raise ValueError("INVALID_PEER_ADDRESS") from exc
    port = int(port_s)
    if not 1 <= port <= 65535:
        raise ValueError("INVALID_PEER_PORT")
    suffix = "/cache" if key is None else "/cache/" + quote(key, safe="")
    return f"http://{host}:{port}{suffix}"


def _open_peer(req):
    # In particular, never follow a response redirect to file:// or localhost.
    return urllib.request.build_opener(_NoRedirect()).open(req, timeout=1.0)

class HashRing:
    """Consistent hashing ring for distributed cache routing."""
    def __init__(self, replicas: int = 150):
        self.replicas = replicas
        self.ring: Dict[int, str] = {}
        self.sorted_keys: List[int] = []

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode('utf-8'), usedforsecurity=False).hexdigest(), 16)

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
            req = urllib.request.Request(_safe_peer_url(primary, key))
            with _open_peer(req) as response:
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
                        _safe_peer_url(node),
                        data=data,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with _open_peer(req) as response:
                        response.read()
                except Exception:
                    pass
        
        if self.local_id not in nodes:
            self.cache.set(key, value, ttl=ttl)
