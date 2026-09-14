"""Unit tests for SovereignTokenBridge in src/sovereign_bridge.py."""
import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src" if (REPO_ROOT / "src").exists() else HERE
sys.path.insert(0, str(SOURCE_ROOT))

from sovereign_bridge import SovereignPointerReceipt, SovereignTokenBridge


class SovereignTokenBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.storage_dir = self.root / "storage"
        self.receipts_path = self.root / "receipts.jsonl"
        self.bridge = SovereignTokenBridge(
            storage_dir=self.storage_dir,
            receipts_path=self.receipts_path,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_externalize_and_resolve(self):
        content = "Sovereign APEX token saver content block " * 20
        receipt = self.bridge.externalize_payload("test_block", content, extra_metadata={"case": "1FDV"})
        
        self.assertEqual(receipt.seq, 1)
        self.assertEqual(receipt.prev_hash, "0" * 64)
        self.assertEqual(receipt.label, "test_block")
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.assertEqual(receipt.sha256, expected_hash)
        self.assertEqual(receipt.canonical_uri, f"sha256://{expected_hash}")
        self.assertGreater(receipt.savings_pct, 0.0)

        # Verify on disk
        stored_file = self.storage_dir / f"{expected_hash}.bin"
        self.assertTrue(stored_file.exists())
        self.assertEqual(stored_file.read_text(encoding="utf-8"), content)

        # Verify resolution
        resolved = self.bridge.resolve_pointer(receipt.canonical_uri)
        self.assertEqual(resolved, content)

    def test_resolve_corruption_detection(self):
        content = "Unaltered content"
        receipt = self.bridge.externalize_payload("integrity_test", content)
        target = self.storage_dir / f"{receipt.sha256}.bin"
        target.write_text("Corrupted content", encoding="utf-8")

        with self.assertRaises(ValueError):
            self.bridge.resolve_pointer(receipt.canonical_uri)

    def test_receipt_chaining(self):
        r1 = self.bridge.externalize_payload("block_1", "payload 1 " * 50)
        r2 = self.bridge.externalize_payload("block_2", "payload 2 " * 50)
        r3 = self.bridge.externalize_payload("block_3", "payload 3 " * 50)

        self.assertEqual(r1.seq, 1)
        self.assertEqual(r2.seq, 2)
        self.assertEqual(r3.seq, 3)

        self.assertEqual(r2.prev_hash, r1.receipt_hash)
        self.assertEqual(r3.prev_hash, r2.receipt_hash)

        # Verify persisted chain in JSONL
        lines = [line.strip() for line in self.receipts_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(lines), 3)
        p1 = json.loads(lines[0])
        p2 = json.loads(lines[1])
        self.assertEqual(p1["receipt_hash"], r1.receipt_hash)
        self.assertEqual(p2["prev_hash"], r1.receipt_hash)

    def test_auto_externalize_if_needed(self):
        small_text = "short text"
        large_text = "large text data " * 100
        payload = {
            "title": small_text,
            "body": large_text,
            "nested": {
                "inner_list": [small_text, large_text]
            }
        }

        mutated_payload, did_mut = self.bridge.auto_externalize_if_needed(payload, threshold_bytes=200)
        self.assertTrue(did_mut)
        self.assertEqual(mutated_payload["title"], small_text)
        self.assertIn("__pointer__", mutated_payload["body"])
        self.assertEqual(mutated_payload["nested"]["inner_list"][0], small_text)
        self.assertIn("__pointer__", mutated_payload["nested"]["inner_list"][1])

        # Resolve the pointer back
        pointer_uri = mutated_payload["body"]["__pointer__"]
        self.assertEqual(self.bridge.resolve_pointer(pointer_uri), large_text)


if __name__ == "__main__":
    unittest.main()
