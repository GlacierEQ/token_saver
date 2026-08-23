import time
from server.discovery import PeerRegistry, UDPBroadcaster, UDPListener

def test_peer_registry():
    registry = PeerRegistry(stale_timeout=1.0)
    registry.add_or_update("127.0.0.1", 8400)
    
    peers = registry.get_active_peers()
    assert len(peers) == 1
    assert peers[0].host == "127.0.0.1"
    assert peers[0].port == 8400
    
    # Test stale
    time.sleep(1.2)
    peers = registry.get_active_peers()
    assert len(peers) == 0
    
    # Test remove
    registry.add_or_update("127.0.0.1", 8400)
    registry.remove("127.0.0.1", 8400)
    assert len(registry.get_active_peers()) == 0

def test_udp_broadcast_listen():
    registry = PeerRegistry()
    listener = UDPListener(registry, listen_port=9999)
    broadcaster = UDPBroadcaster(gateway_port=8400, broadcast_port=9999, interval=0.1)
    
    listener.start()
    broadcaster.start()
    
    time.sleep(0.5)
    
    broadcaster.stop()
    listener.stop()
    
    peers = registry.get_active_peers()
    assert len(peers) >= 1
    assert any(p.port == 8400 for p in peers)
