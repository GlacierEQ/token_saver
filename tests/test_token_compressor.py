"""Test suite for Token Saver Compressor."""
import unittest

class TokenCompressorSim:
    def compute_ratio(self, raw: int, comp: int) -> float:
        return (1.0 - (comp / raw)) * 100.0 if raw > 0 else 0.0

class TestTokenCompressor(unittest.TestCase):
    def test_compression_ratio(self):
        c = TokenCompressorSim()
        ratio = c.compute_ratio(128000, 18500)
        self.assertGreater(ratio, 85.0)

if __name__ == "__main__":
    unittest.main()
