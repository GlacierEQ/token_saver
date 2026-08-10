#!/usr/bin/env python3
"""Deterministic Token Saver benchmark suite — drives shipped APIs only."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from pure_pointer import externalize, measure  # noqa: E402
from token_saver_elite_core import EliteMemoryCache, EliteTokenBridge  # noqa: E402


def run() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        cache = EliteMemoryCache(str(Path(tmp) / "cache"))
        bridge = EliteTokenBridge(cache)
        miss = cache.get("missing")
        cache.set("known", {}, ttl=3600, source="benchmark")
        hit = cache.get("known")
        cache_result = {
            "miss_is_none": miss is None,
            "hit_value": hit,
            "hits": cache.stats["hits"],
            "misses": cache.stats["misses"],
            "optimized_bytes_before": cache.stats["optimized_bytes_before"],
            "optimized_bytes_after": cache.stats["optimized_bytes_after"]
        }
        context = "\n".join(f"line-{i}: deterministic context" for i in range(100))
        compressed = bridge.compress_context(context, compression_ratio=0.1)
        compression_result = {
            "input_lines": len(context.splitlines()),
            "output_lines": len(compressed.splitlines()),
            "input_bytes": len(context.encode()),
            "output_bytes": len(compressed.encode())
        }
        requests = [
            {"type": "query", "model": "local", "query": f"q{i}", "tokens": 100}
            for i in range(3)
        ]
        batched = bridge.batch_requests(requests)
        batching_result = {
            "input_requests": len(requests),
            "output_requests": len(batched),
            "request_count": batched[0].get("request_count", 1),
            "savings_status": batched[0].get("savings_status", "n/a")
        }
        pointer = measure(externalize("hello world " * 500, Path(tmp) / "pointers"))
        return {
            "cache_hit_miss": cache_result,
            "compression": compression_result,
            "batching": batching_result,
            "pointer_externalization": pointer
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(run(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
