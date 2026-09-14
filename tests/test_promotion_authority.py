from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from src.promotion_authority import (
    PROMOTION_SECRET_ENV,
    PromotionAuthority,
    promotion_secret_from_environment,
    verify_bound_grant,
)

ROOT = Path(__file__).resolve().parents[1]


class PromotionAuthTests(unittest.TestCase):
    def test_issue_verify(self):
        authority = PromotionAuthority(b"test-secret", ttl_s=60)
        grant = authority.issue("GlacierEQ/x", "abc", "def", now=1000.0)
        ok, _ = authority.verify(grant, now=1001.0)
        self.assertTrue(ok)

    def test_expired(self):
        authority = PromotionAuthority(b"test-secret", ttl_s=10)
        grant = authority.issue("GlacierEQ/x", "abc", "def", now=1000.0)
        ok, reason = authority.verify(grant, now=2000.0)
        self.assertFalse(ok)
        self.assertEqual(reason, "GRANT_EXPIRED")

    def test_real_machine_grant_verifies_against_proof_receipt(self):
        grant_path = ROOT / "machine" / "promotion_authority.json"
        proof_path = ROOT / "machine" / "proof_receipt.json"
        if not grant_path.is_file() or not proof_path.is_file():
            self.skipTest("receipts not yet bound")
        grant = json.loads(grant_path.read_text())
        proof = json.loads(proof_path.read_text())
        file_digest = hashlib.sha256(proof_path.read_bytes()).hexdigest()
        self.assertEqual(grant["proof_receipt_digest"], file_digest)
        self.assertEqual(grant["source_sha"], proof["source_sha"])
        ok, reason = verify_bound_grant(
            grant,
            proof_path,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "PROMOTION_SECRET_REQUIRED")

    def test_explicit_secret_is_required_for_bound_grants(self):
        receipt = {"source_sha": "abc"}
        proof_path = ROOT / "machine" / "proof_receipt.json"
        original = proof_path.read_bytes()
        try:
            proof_path.write_text(json.dumps(receipt), encoding="utf-8")
            digest = hashlib.sha256(proof_path.read_bytes()).hexdigest()
            authority = PromotionAuthority(b"test-secret", ttl_s=60)
            grant = authority.issue("GlacierEQ/x", "abc", digest, now=1000.0)
            ok, reason = verify_bound_grant(
                grant.__dict__, proof_path, secret=b"test-secret", now=1001.0
            )
            self.assertTrue(ok, reason)
        finally:
            proof_path.write_bytes(original)

    def test_environment_secret_requires_explicit_injection(self):
        self.assertIsNone(promotion_secret_from_environment({}))
        self.assertEqual(
            promotion_secret_from_environment({PROMOTION_SECRET_ENV: "dev-secret"}),
            b"dev-secret",
        )


if __name__ == "__main__":
    unittest.main()
