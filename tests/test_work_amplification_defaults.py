"""Regression gate: conserve waste, never silently shrink the mission."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from src.unified_token_engine import UnifiedTokenEngine
from token_saver_elite_core import EliteMemoryCache, EliteTokenBridge
from mcp.server import TokenSaverMCPServer


def full_context():
    return "\n\n".join(
        f"Evidence record {i}: identity, date, source, contradiction, next authorized action, and verification requirement {i}."
        for i in range(45)
    )


def unified(tmp_path):
    return UnifiedTokenEngine(work_dir=tmp_path / "sources", receipts_path=tmp_path / "receipts.jsonl")


def test_default_unified_is_full_context_and_source_preserving(tmp_path):
    engine = unified(tmp_path)
    context = full_context()
    evidence = [{"source_id": f"source-{i}", "content": f"Native record and exhibit {i}." * 20} for i in range(6)]
    payload = {"mission_id": "CASE-1009", "objective": "Obtain evidence and seek appropriate custody relief", "context": context, "evidence": evidence, "continuation_cursor": "docket190"}
    original = copy.deepcopy(payload)
    result = engine.optimize_message_payload(payload)
    assert payload == original
    assert result["payload"] == original
    assert result["metrics"]["bytes_saved"] == 0
    assert result["metrics"]["stage1_externalized"] is False
    assert result["metrics"]["mission_context_preserved"] is True
    assert result["metrics"]["lossy_compression_applied"] is False
    assert not (tmp_path / "receipts.jsonl").exists()


def test_explicit_document_offload_does_not_hide_active_mission_context(tmp_path):
    engine = unified(tmp_path)
    context = full_context()
    document = "Historical source document attachment " * 60
    payload = {"mission_id": "CASE-1009", "context": context, "evidence": {"date": "2025-06-19", "source": context}, "document": document}
    result = engine.optimize_message_payload(payload, offload_threshold_bytes=300, compression_ratio=0.2)
    assert result["payload"]["mission_id"] == payload["mission_id"]
    assert result["payload"]["context"] == context
    assert result["payload"]["evidence"] == payload["evidence"]
    assert result["metrics"]["lossy_compression_applied"] is False
    assert result["metrics"]["lossy_compression_blocked"] is True
    assert result["metrics"]["stage1_externalized"] is True
    assert engine.bridge.resolve_pointer(result["payload"]["document"]["__pointer__"]) == document


def test_explicit_extraction_requires_consent_and_recoverable_original(tmp_path):
    engine = unified(tmp_path)
    context = full_context()
    payload = {"context": context, "mission_id": "M-1"}
    result = engine.optimize_message_payload(payload, compression_ratio=0.18, allow_lossy_context=True)
    assert result["payload"]["context"] != context
    assert result["metrics"]["lossy_compression_applied"] is True
    assert result["metrics"]["mission_context_preserved"] is False
    recovery = result["metrics"]["original_context_pointer"]
    assert engine.bridge.resolve_pointer(recovery) == context
    assert result["payload"]["mission_id"] == "M-1"


def test_reject_invalid_compression_contract_before_any_side_effect(tmp_path):
    engine = unified(tmp_path)
    for ratio in (0, -0.25, 1.01):
        with pytest.raises(ValueError):
            engine.optimize_message_payload({"context": full_context()}, compression_ratio=ratio)
    with pytest.raises(ValueError):
        engine.optimize_message_payload({"context": full_context()}, offload_threshold_bytes=0)
    assert not (tmp_path / "receipts.jsonl").exists()


def test_elite_default_preserves_full_context_and_records_zero_fake_savings(tmp_path):
    cache = EliteMemoryCache(str(tmp_path))
    bridge = EliteTokenBridge(cache)
    request = {"mission_id": "M-1", "context": full_context()}
    snapshot = copy.deepcopy(request)
    first = bridge.optimize_request(request)
    second = bridge.optimize_request(request)
    assert request == snapshot
    assert first["context"] == snapshot["context"]
    assert first["measurement"]["saved"] == 0
    assert first["measurement"]["context_policy"] == "preserved_by_default"
    assert first["cache"]["hit"] is False
    assert second["cache"]["hit"] is True


def test_elite_direct_compression_is_preserving_unless_explicit_ratio(tmp_path):
    bridge = EliteTokenBridge(EliteMemoryCache(str(tmp_path)))
    text = full_context()
    assert bridge.compress_context(text) == text
    compact = bridge.compress_context(text, compression_ratio=0.2)
    assert compact != text
    assert "[ptr:sha256://" in compact
    assert any(p.read_text(encoding="utf-8") == text for p in (tmp_path / "pointers").glob("*") if p.is_file())


def test_gateway_default_optimize_keeps_all_work(monkeypatch, tmp_path):
    import server.gateway as gateway
    from server.gateway import GatewayHandler
    monkeypatch.setattr(gateway, "bridge", EliteTokenBridge(EliteMemoryCache(str(tmp_path))))
    out = {}
    handler = GatewayHandler.__new__(GatewayHandler)
    handler._read_json = lambda: {"text": full_context()}
    handler._send_json = lambda status, body: out.update({"status": status, "body": body})
    handler._handle_post_optimize()
    assert out["status"] == 200
    assert out["body"]["optimized"] == full_context()
    assert out["body"]["measurements"]["saved"] == 0


def test_mcp_does_not_fabricate_outcomes_or_savings(tmp_path):
    server = TokenSaverMCPServer(cache=EliteMemoryCache(str(tmp_path / "cache")))
    original = full_context()
    compressed = server.call_tool("compress_context", {"text": original, "ratio": 1.0, "model": "gpt-4"})
    assert compressed["compressed"] == original
    assert compressed["tokens_saved"] == 0
    request = {"context": original, "mission_id": "M-1"}
    optimized = server.call_tool("optimize_request", {"request": request, "ttl": 3600})
    assert optimized["context"] == original
    assert optimized["measurement"]["saved"] == 0
    assert server.call_tool("cache_status", {})["hits"] == 0
    pointer = server.call_tool("externalize", {"text": original, "label": "source", "dest": str(tmp_path / "blobs")})
    assert pointer["pointer_uri"] == "sha256://" + hashlib.sha256(original.encode("utf-8")).hexdigest()
    assert pointer["savings_status"] == "bytes_only"
    assert any(x.read_text(encoding="utf-8") == original for x in (tmp_path / "blobs").rglob("*") if x.is_file())

def test_pointer_refuses_ephemeral_only_source_storage(tmp_path, monkeypatch):
    from src import pure_pointer
    monkeypatch.setattr(pure_pointer, "get_free_disk_gb", lambda _: 0.1)
    with pytest.raises(OSError, match="INSUFFICIENT_PERSISTENT_STORAGE"):
        pure_pointer.externalize("Native evidence cannot be lost " * 20, tmp_path, label="evidence")
    assert not list(tmp_path.glob("*.txt"))


def test_pointer_recovery_never_uses_process_only_mock_store(tmp_path):
    from src import pure_pointer
    original = "Evidence source with native provenance " * 30
    pointer = pure_pointer.externalize(original, tmp_path, label="native")
    Path(pointer.path).unlink()
    # The legacy mock is not a durable remote store. Its presence is not proof.
    pure_pointer.MockRemoteStore.put(pointer.sha256, original.encode("utf-8"))
    with pytest.raises(FileNotFoundError):
        pure_pointer.resolve(pointer, allowed_root=tmp_path)


def test_legacy_truncated_cache_entry_cannot_replay(tmp_path):
    from token_saver_elite_core import sha256_key
    cache = EliteMemoryCache(str(tmp_path))
    request = {"context": full_context(), "mission_id": "M-1"}
    cache.set(f"request:sha256:{sha256_key(request)}", {"context": "legacy-shortened"})
    bridge = EliteTokenBridge(cache)
    fresh = bridge.optimize_request(request)
    assert fresh["context"] == request["context"]
    assert fresh["cache"]["hit"] is False

def test_source_pointer_write_never_calls_disposable_cache_eviction(tmp_path, monkeypatch):
    from src import pure_pointer
    def destructive_eviction(*_args, **_kwargs):
        raise AssertionError("Persistent source was subjected to automatic LRU eviction")
    monkeypatch.setattr(pure_pointer, "enforce_lru_quota", destructive_eviction)
    content = "Persist an exact case source without pruning " * 30
    ptr = pure_pointer.externalize(content, tmp_path, label="original")
    assert pure_pointer.resolve(ptr, allowed_root=tmp_path) == content
