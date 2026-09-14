import json
import socket
import threading
import time
import urllib.error
import urllib.request

from server.gateway import TokenGateway


def _find_free_port() -> int:
    """Find an available port by binding to port 0."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_gateway():
    port = _find_free_port()
    gateway = TokenGateway(port=port)
    base = f"http://127.0.0.1:{port}"

    t = threading.Thread(target=gateway.start, daemon=True)
    t.start()

    time.sleep(0.5)  # wait for server to start

    try:
        # Test /health
        req = urllib.request.Request(f"{base}/health")
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            data = json.loads(response.read())
            assert data["status"] == "ok"
            assert "version" in data

        # Test POST /cache
        data = json.dumps({"key": "test_key", "value": "test_value"}).encode("utf-8")
        req = urllib.request.Request(
            f"{base}/cache",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as response:
            assert response.status == 201

        # Test GET /cache/<key>
        req = urllib.request.Request(f"{base}/cache/test_key")
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            data = json.loads(response.read())
            assert data["value"] == "test_value"

        # Test POST /optimize
        data = json.dumps(
            {"text": "line1\nline2\nline3\nline4\nline5", "ratio": 0.5}
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{base}/optimize",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            data = json.loads(response.read())
            assert "optimized" in data
            assert "measurements" in data

        # Test /metrics
        req = urllib.request.Request(f"{base}/metrics")
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            text = response.read().decode("utf-8")
            assert "token_saver_requests_total" in text
            assert "token_saver_cache_hits_total" in text

    finally:
        gateway.stop()
