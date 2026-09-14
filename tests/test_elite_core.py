import copy
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0, str(REPO_ROOT if (REPO_ROOT / "token_saver_elite_core.py").exists() else HERE)
)

from token_saver_elite_core import EliteMemoryCache, EliteTokenBridge, sha256_key


class EliteCoreTests(unittest.TestCase):
    def test_sha256_key_is_stable_and_full_length(self):
        first = sha256_key({"b": 2, "a": 1})
        second = sha256_key({"a": 1, "b": 2})
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_optimize_does_not_mutate_input_and_persists_cache(self):
        with TemporaryDirectory() as directory:
            cache = EliteMemoryCache(directory)
            bridge = EliteTokenBridge(cache)
            request = {
                "query": "q",
                "context": "\n".join(f"line-{i}" for i in range(20)),
            }
            original = copy.deepcopy(request)
            first = bridge.optimize_request(request)
            second = bridge.optimize_request(request)
            self.assertEqual(request, original)
            self.assertNotEqual(first["context"], request["context"])
            self.assertGreater(first["measurement"]["saved"], 0)
            self.assertEqual(first["cache"]["algorithm"], "sha256")
            self.assertFalse(first["cache"]["hit"])
            self.assertTrue(first["cache"]["stored"])
            self.assertTrue(second["cache"]["hit"])
            reloaded = EliteMemoryCache(directory)
            self.assertEqual(
                reloaded.get(first["cache"]["key"])["context"], first["context"]
            )

    def test_batch_does_not_fabricate_savings(self):
        with TemporaryDirectory() as directory:
            bridge = EliteTokenBridge(EliteMemoryCache(directory))
            batched = bridge.batch_requests(
                [
                    {"type": "query", "model": "local", "query": "a"},
                    {"type": "query", "model": "local", "query": "b"},
                ]
            )
            self.assertEqual(batched[0]["request_count"], 2)
            self.assertEqual(batched[0]["savings_status"], "not_measured")
            self.assertNotIn("token_estimate_after", batched[0])

    def test_write_failure_rolls_back_new_entry_without_breaking_reads(self):
        with TemporaryDirectory() as directory:
            cache = EliteMemoryCache(directory)
            self.assertTrue(cache.set("existing", {"ok": True}))
            cache._save_cache = lambda: False
            self.assertFalse(cache.set("new", {"ok": False}))
            self.assertNotIn("new", cache.memory)
            self.assertEqual(cache.get("existing"), {"ok": True})

    def test_cache_hit_does_not_block_on_full_cache_fsync(self):
        with TemporaryDirectory() as directory:
            cache = EliteMemoryCache(directory)
            self.assertTrue(cache.set("existing", {"ok": True}))
            cache._save_cache = lambda: self.fail(
                "cache hit attempted synchronous persistence"
            )
            self.assertEqual(cache.get("existing"), {"ok": True})

    def test_invalid_entry_does_not_discard_valid_entries(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            valid = {
                "key": "valid",
                "value": {"ok": True},
                "ttl": 3600,
                "created_at": 4102444800.0,
                "source": "test",
                "hits": 0,
            }
            (root / "cache.json").write_text(
                json.dumps(
                    {
                        "cache": {"invalid": {"unknown": True}, "valid": valid},
                        "stats": {},
                    }
                ),
                encoding="utf-8",
            )
            cache = EliteMemoryCache(directory)
            self.assertEqual(cache.get("valid"), {"ok": True})
            self.assertNotIn("invalid", cache.memory)


if __name__ == "__main__":
    unittest.main()
