import hashlib
import hmac
import unittest

from orchestrator.approval import (
    build_approval_envelope,
    md5_novelty_hex,
    sha256_hex,
    verify_approval,
)


class ApprovalTests(unittest.TestCase):
    def test_builds_and_verifies_hmac_approval_envelope(self):
        secret = b"approval-secret"
        diff = b"change"

        envelope = build_approval_envelope(secret, b"base", b"proposed", diff)

        self.assertEqual(envelope.base_snapshot_sha256, hashlib.sha256(b"base").hexdigest())
        self.assertEqual(envelope.proposed_snapshot_sha256, hashlib.sha256(b"proposed").hexdigest())
        self.assertEqual(envelope.diff_sha256, sha256_hex(diff))
        self.assertEqual(envelope.diff_hmac_sha256, hmac.digest(secret, diff, "sha256").hex())
        self.assertTrue(verify_approval(secret, diff, envelope.diff_hmac_sha256))
        self.assertFalse(verify_approval(secret, b"tampered", envelope.diff_hmac_sha256))

    def test_md5_novelty_is_canonical_and_not_security_hash(self):
        first = md5_novelty_hex({"b": 2, "a": 1})
        second = md5_novelty_hex({"a": 1, "b": 2})

        self.assertEqual(first, second)
        self.assertEqual(len(first), 32)


if __name__ == "__main__":
    unittest.main()
