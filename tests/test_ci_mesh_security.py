"""Security and operational regressions exposed by restored public CI."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from server.mesh import HashRing, _safe_peer_url, _NoRedirect


def test_hash_ring_keeps_existing_distribution_without_security_md5_use():
    ring = HashRing(replicas=3)
    key = "replica-1"
    # Noncryptographic cache placement only; existing ring identities must remain stable.
    assert ring._hash(key) == int(hashlib.md5(key.encode("utf-8"), usedforsecurity=False).hexdigest(), 16)


def test_peer_url_rejects_injection_and_bad_ports():
    invalid = [
        "127.0.0.1:0",
        "127.0.0.1:65536",
        "127.0.0.1:abc",
        "127.0.0.1:80@evil.example",
        "127.0.0.1:80/path",
        "http://127.0.0.1:8400",
    ]
    for candidate in invalid:
        with pytest.raises(ValueError):
            _safe_peer_url(candidate, "key")
    assert _safe_peer_url("127.0.0.1:8400", "a/b?c") == "http://127.0.0.1:8400/cache/a%2Fb%3Fc"


def test_redirects_are_not_silently_followed_to_external_target():
    handler = _NoRedirect()
    assert handler.redirect_request(None, None, 302, "Moved", {}, "file:///tmp/private") is None


def test_discovery_rejects_nonnumeric_and_out_of_range_port():
    from server.discovery import PeerRegistry
    registry = PeerRegistry()
    for bad in ("8400", 0, -1, 65536, True):
        with pytest.raises(ValueError):
            registry.add_or_update("127.0.0.1", bad)
    assert registry.get_active_peers() == []


def test_sidecar_imports_and_returns_measured_health(tmp_path):
    from mastermind_sidecar import MastermindSidecar
    sidecar = MastermindSidecar(home_dir=str(tmp_path))
    report = json.loads(sidecar.status())
    assert report["status"] in {"healthy", "degraded", "unhealthy"}
    assert isinstance(report["checks"], dict)
    assert isinstance(report["details"], dict)
