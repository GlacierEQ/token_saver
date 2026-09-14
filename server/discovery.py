import socket
import json
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Peer:
    """Represents a discovered peer in the network."""
    host: str
    port: int
    last_seen: float
    status: str = "active"
    
    @property
    def id(self) -> str:
        """Return the unique ID of the peer."""
        return f"{self.host}:{self.port}"

class PeerRegistry:
    """Thread-safe registry of known peers."""
    def __init__(self, stale_timeout: float = 30.0):
        self.peers: Dict[str, Peer] = {}
        self.lock = threading.Lock()
        self.stale_timeout = stale_timeout

    def add_or_update(self, host: str, port: int) -> None:
        """Add a new peer or update the last_seen time of an existing one."""
        with self.lock:
            peer_id = f"{host}:{port}"
            if peer_id in self.peers:
                self.peers[peer_id].last_seen = time.time()
                self.peers[peer_id].status = "active"
            else:
                self.peers[peer_id] = Peer(host=host, port=port, last_seen=time.time())

    def remove(self, host: str, port: int) -> None:
        """Remove a peer from the registry."""
        with self.lock:
            peer_id = f"{host}:{port}"
            self.peers.pop(peer_id, None)

    def get_active_peers(self) -> List[Peer]:
        """Get a list of currently active peers."""
        with self.lock:
            now = time.time()
            active = []
            for peer in self.peers.values():
                if now - peer.last_seen > self.stale_timeout:
                    peer.status = "stale"
                if peer.status == "active":
                    active.append(peer)
            return active

class UDPBroadcaster:
    """Sends periodic UDP announcements."""
    def __init__(self, gateway_port: int, broadcast_port: int = 8401, interval: float = 5.0):
        self.gateway_port = gateway_port
        self.broadcast_port = broadcast_port
        self.interval = interval
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the broadcasting loop in a background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop the broadcasting loop."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.sock.close()

    def _run(self) -> None:
        payload = json.dumps({
            "service": "token_saver",
            "port": self.gateway_port,
            "version": "4.0.0"
        }).encode('utf-8')
        
        while self.running:
            try:
                self.sock.sendto(payload, ('<broadcast>', self.broadcast_port))
            except Exception:
                pass
            time.sleep(self.interval)

class UDPListener:
    """Listens for peer announcements."""
    def __init__(self, registry: PeerRegistry, listen_port: int = 8401):
        self.registry = registry
        self.listen_port = listen_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
        self.sock.bind(('', self.listen_port))
        self.sock.settimeout(1.0)
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the listening loop in a background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop the listening loop."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self.sock.close()

    def _run(self) -> None:
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                host = addr[0]
                msg = json.loads(data.decode('utf-8'))
                if msg.get("service") == "token_saver" and "port" in msg:
                    self.registry.add_or_update(host, msg["port"])
            except socket.timeout:
                continue
            except Exception:
                continue

def discover_peers(timeout: float = 5.0, listen_port: int = 8401) -> List[Peer]:
    """Perform a one-shot scan for peers."""
    registry = PeerRegistry()
    listener = UDPListener(registry, listen_port=listen_port)
    listener.start()
    time.sleep(timeout)
    listener.stop()
    return registry.get_active_peers()
