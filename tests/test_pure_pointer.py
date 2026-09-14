import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src" if (REPO_ROOT / "src").exists() else HERE
sys.path.insert(0, str(SOURCE_ROOT))

from pure_pointer import externalize, measure, resolve, verify


class PurePointerTests(unittest.TestCase):
    def test_round_trip_uses_full_sha256(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            body = "hello world " * 500
            pointer = externalize(body, root, "case payload")
            result = measure(pointer)
            self.assertEqual(len(pointer.sha256), 64)
            self.assertEqual(pointer.canonical_uri, f"sha256://{pointer.sha256}")
            self.assertEqual(resolve(pointer, root), body)
            self.assertTrue(verify(pointer, root))
            self.assertLess(result["bytes_out"], result["bytes_in"])
            self.assertGreater(result["savings_pct"], 0.0)
            self.assertEqual(result["measurement_unit"], "utf8_bytes")
            self.assertEqual(result["sha256"], pointer.sha256)
            self.assertEqual(result["canonical_uri"], pointer.canonical_uri)

    def test_corruption_is_detected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            pointer = externalize("original", root)
            Path(pointer.path).write_text("changed", encoding="utf-8")
            self.assertFalse(verify(pointer, root))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                resolve(pointer, root)

    def test_path_escape_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / "outside-token-saver-test.txt"
            outside.write_text("outside", encoding="utf-8")
            try:
                pointer = externalize("inside", root)
                escaped = replace(pointer, path=str(outside))
                with self.assertRaisesRegex(ValueError, "outside the allowed root"):
                    resolve(escaped, root)
            finally:
                outside.unlink(missing_ok=True)

    def test_concurrent_externalize_uses_unique_temporary_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            body = "concurrent payload" * 100
            with ThreadPoolExecutor(max_workers=8) as pool:
                pointers = list(
                    pool.map(lambda _: externalize(body, root, "same"), range(24))
                )
            self.assertTrue(all(resolve(pointer, root) == body for pointer in pointers))
            self.assertEqual(len({pointer.sha256 for pointer in pointers}), 1)
            self.assertEqual(list(root.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
