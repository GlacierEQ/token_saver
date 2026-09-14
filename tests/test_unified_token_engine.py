"""Unit tests for UnifiedTokenEngine in src/unified_token_engine.py."""
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src" if (REPO_ROOT / "src").exists() else HERE
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SOURCE_ROOT))

from unified_token_engine import UnifiedTokenEngine


class UnifiedTokenEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.storage_dir = self.root / "storage"
        self.receipts_path = self.root / "receipts.jsonl"
        self.engine = UnifiedTokenEngine(
            work_dir=self.storage_dir,
            receipts_path=self.receipts_path,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_small_payload_unmodified(self):
        payload = {
            "role": "user",
            "message": "hello token saver",
        }
        res = self.engine.optimize_message_payload(payload, offload_threshold_bytes=500)
        self.assertEqual(res["status"], "OPTIMIZED")
        self.assertFalse(res["metrics"]["stage1_externalized"])
        self.assertEqual(res["payload"], payload)

    def test_dual_stage_optimization(self):
        large_document = "Important sovereign legal doctrine statement with verified truth. " * 30
        long_context = "Context item number: " + ("\nDetail: repetitive contextual metadata" * 40)
        payload = {
            "session_id": "sess_12345",
            "document": large_document,
            "context": long_context,
        }

        res = self.engine.optimize_message_payload(
            payload,
            offload_threshold_bytes=300,
            compression_ratio=0.5,
        )

        self.assertEqual(res["status"], "OPTIMIZED")
        self.assertTrue(res["metrics"]["stage1_externalized"])
        self.assertGreater(res["metrics"]["bytes_saved"], 0)
        self.assertGreater(res["metrics"]["tokens_saved"], 0)
        self.assertGreater(res["metrics"]["savings_pct"], 0.0)

        # Check that document was externalized to pointer
        opt_doc = res["payload"]["document"]
        self.assertIn("__pointer__", opt_doc)
        self.assertIn("sha256://", opt_doc["__pointer__"])

        # Check that pointer resolves properly
        resolved = self.engine.bridge.resolve_pointer(opt_doc["__pointer__"])
        self.assertEqual(resolved, large_document)


if __name__ == "__main__":
    unittest.main()
