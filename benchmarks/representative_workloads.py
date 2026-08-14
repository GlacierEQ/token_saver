"""Measure fixed prompt-shaped workloads; not model-token or quality claims."""

import importlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

token_saver_elite_core = importlib.import_module("token_saver_elite_core")
EliteMemoryCache = token_saver_elite_core.EliteMemoryCache
EliteTokenBridge = token_saver_elite_core.EliteTokenBridge

WORKLOADS = {
    "case_timeline": "Case timeline request:\n"
    + "Verified event and provenance note.\n" * 80,
    "technical_review": "Review request:\n"
    + "Architecture, test, and reproducibility criterion.\n" * 80,
    "support_summary": "Support summary request:\n"
    + "Account recovery evidence and next lawful step.\n" * 80,
}


def run() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        bridge = EliteTokenBridge(EliteMemoryCache(tmp))
        results = {}
        for name, prompt in WORKLOADS.items():
            reduced = bridge.compress_context(prompt, compression_ratio=0.1)
            results[name] = {
                "input_bytes": len(prompt.encode()),
                "output_bytes": len(reduced.encode()),
                "input_lines": len(prompt.splitlines()),
                "output_lines": len(reduced.splitlines()),
            }
        return {
            "workloads": results,
            "measurement": "fixture byte and line counts only",
        }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
