"""Benchmark assertions against shipped Token Saver APIs (measured, not frozen folklore)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from benchmark_token_saver import run


def test_deterministic_benchmarks():
    result = run()
    cache = result["cache_hit_miss"]
    assert cache["miss_is_none"] is True
    assert isinstance(cache["hit_value"], dict) and len(cache["hit_value"]) >= 1
    assert cache["hits"] == 1
    assert cache["misses"] == 1

    comp = result["compression"]
    assert comp["input_lines"] == 100
    assert 3 <= comp["output_lines"] < comp["input_lines"]
    assert comp["output_bytes"] < comp["input_bytes"]

    batch = result["batching"]
    assert batch["input_requests"] == 3
    assert batch["output_requests"] == 1
    assert batch["request_count"] == 3

    ptr = result["pointer_externalization"]
    assert ptr["bytes_in"] == 6000
    assert ptr["bytes_out"] < ptr["bytes_in"]
    assert ptr["savings_pct"] > 90.0
