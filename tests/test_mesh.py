from collections import Counter
from server.mesh import HashRing, DistributedCache
from server.discovery import PeerRegistry
from typing import Any

class MockEliteMemoryCache:
    def __init__(self):
        self.data = {}
        
    def get(self, key: str) -> Any:
        return self.data.get(key)
        
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        self.data[key] = value

def test_hash_ring_distribution():
    ring = HashRing(replicas=150)
    nodes = ["node1", "node2", "node3", "node4", "node5"]
    for node in nodes:
        ring.add_node(node)
        
    counts = Counter()
    for i in range(10000):
        node = ring.get_node(f"key{i}")
        counts[node] += 1
        
    expected = 10000 / len(nodes)
    for node in nodes:
        assert expected * 0.7 <= counts[node] <= expected * 1.3
        
def test_hash_ring_add_remove():
    ring = HashRing(replicas=150)
    ring.add_node("node1")
    assert ring.get_node("test") == "node1"
    
    ring.add_node("node2")
    ring.remove_node("node1")
    assert ring.get_node("test") == "node2"
    
def test_hash_ring_get_nodes():
    ring = HashRing(replicas=1)
    ring.add_node("node1")
    ring.add_node("node2")
    ring.add_node("node3")
    
    nodes = ring.get_nodes("test", count=2)
    assert len(nodes) == 2
    assert len(set(nodes)) == 2

def test_distributed_cache_fallback():
    registry = PeerRegistry()
    local_cache = MockEliteMemoryCache()
    # local_id is used by HashRing directly, registry is empty initially
    cache = DistributedCache("local:8400", local_cache, registry)
    
    cache.set("key1", "val1")
    assert local_cache.get("key1") == "val1"
    assert cache.get("key1") == "val1"
