import json
import time
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from typing import Any

from token_saver_elite_core import EliteMemoryCache, EliteTokenBridge
from server.discovery import PeerRegistry, UDPBroadcaster, UDPListener

class Metrics:
    def __init__(self):
        self.requests = 0
        self.errors = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.bytes_saved = 0
        self.start_time = time.time()

metrics = Metrics()
cache = EliteMemoryCache(None)
bridge = EliteTokenBridge(cache)
registry = PeerRegistry()

class GatewayHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        start = time.time()
        metrics.requests += 1
        parsed = urlparse(self.path)
        path = parsed.path
        
        try:
            if path == "/health":
                self._handle_health()
            elif path.startswith("/cache/"):
                key = path[len("/cache/"):]
                self._handle_get_cache(key)
            elif path == "/metrics":
                self._handle_metrics()
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            metrics.errors += 1
            self.send_error(500, str(e))

    def do_POST(self) -> None:
        start = time.time()
        metrics.requests += 1
        parsed = urlparse(self.path)
        path = parsed.path
        
        try:
            if path == "/cache":
                self._handle_post_cache()
            elif path == "/optimize":
                self._handle_post_optimize()
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            metrics.errors += 1
            self.send_error(500, str(e))

    def _handle_health(self) -> None:
        data = {
            "status": "ok",
            "uptime": time.time() - metrics.start_time,
            "peers": len(registry.get_active_peers()),
            "version": "4.0.0"
        }
        self._send_json(200, data)

    def _handle_get_cache(self, key: str) -> None:
        val = cache.get(key)
        if val is None:
            metrics.cache_misses += 1
            self.send_error(404, "Key not found")
        else:
            metrics.cache_hits += 1
            self._send_json(200, {"key": key, "value": val})

    def _handle_post_cache(self) -> None:
        body = self._read_json()
        if not body or "key" not in body or "value" not in body:
            self.send_error(400, "Bad Request")
            return
            
        key = body["key"]
        val = body["value"]
        ttl = body.get("ttl", 3600)
        
        cache.set(key, val, ttl=ttl)
        self._send_json(201, {"status": "created"})

    def _handle_post_optimize(self) -> None:
        body = self._read_json()
        if not body or "text" not in body:
            self.send_error(400, "Bad Request")
            return
            
        text = body["text"]
        ratio = body.get("ratio", 0.5)
        
        optimized = bridge.compress_context(text, compression_ratio=ratio)
        saved = len(text) - len(optimized)
        if saved > 0:
            metrics.bytes_saved += saved
            
        self._send_json(200, {
            "optimized": optimized,
            "measurements": {
                "original_len": len(text),
                "optimized_len": len(optimized),
                "saved": saved
            }
        })

    def _handle_metrics(self) -> None:
        lines = [
            "# HELP token_saver_requests_total Total number of HTTP requests.",
            "# TYPE token_saver_requests_total counter",
            f"token_saver_requests_total {metrics.requests}",
            "# HELP token_saver_errors_total Total number of HTTP errors.",
            "# TYPE token_saver_errors_total counter",
            f"token_saver_errors_total {metrics.errors}",
            "# HELP token_saver_cache_hits_total Total cache hits.",
            "# TYPE token_saver_cache_hits_total counter",
            f"token_saver_cache_hits_total {metrics.cache_hits}",
            "# HELP token_saver_cache_misses_total Total cache misses.",
            "# TYPE token_saver_cache_misses_total counter",
            f"token_saver_cache_misses_total {metrics.cache_misses}",
            "# HELP token_saver_bytes_saved_total Total bytes saved by compression.",
            "# TYPE token_saver_bytes_saved_total counter",
            f"token_saver_bytes_saved_total {metrics.bytes_saved}"
        ]
        
        self.send_response(200)
        self.send_header("Content-type", "text/plain; version=0.0.4")
        self.end_headers()
        self.wfile.write(("\n".join(lines) + "\n").encode("utf-8"))

    def _read_json(self) -> Any:
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return None
        body = self.rfile.read(content_length)
        return json.loads(body.decode("utf-8"))

    def _send_json(self, status: int, data: Any) -> None:
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

class TokenGateway:
    def __init__(self, port: int = 8400):
        self.port = port
        self.server = ThreadingHTTPServer(('127.0.0.1', port), GatewayHandler)
        self.broadcaster = UDPBroadcaster(gateway_port=port)
        self.listener = UDPListener(registry)

    def start(self) -> None:
        self.broadcaster.start()
        self.listener.start()
        self.server.serve_forever()

    def stop(self) -> None:
        self.broadcaster.stop()
        self.listener.stop()
        self.server.shutdown()
        self.server.server_close()

def main() -> None:
    parser = argparse.ArgumentParser(description="Token Saver Gateway")
    parser.add_argument("--port", type=int, default=8400, help="Port to bind")
    args = parser.parse_args()
    
    gateway = TokenGateway(port=args.port)
    try:
        gateway.start()
    except KeyboardInterrupt:
        gateway.stop()

if __name__ == "__main__":
    main()
