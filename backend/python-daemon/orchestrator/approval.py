from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiffApprovalEnvelope:
    base_snapshot_sha256: str
    proposed_snapshot_sha256: str
    diff_sha256: str
    diff_hmac_sha256: str


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5_novelty_hex(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.md5(canonical, usedforsecurity=False).hexdigest()


def build_approval_envelope(
    secret: bytes,
    base_bytes: bytes,
    proposed_bytes: bytes,
    diff_bytes: bytes,
) -> DiffApprovalEnvelope:
    return DiffApprovalEnvelope(
        base_snapshot_sha256=sha256_hex(base_bytes),
        proposed_snapshot_sha256=sha256_hex(proposed_bytes),
        diff_sha256=sha256_hex(diff_bytes),
        diff_hmac_sha256=hmac.digest(secret, diff_bytes, "sha256").hex(),
    )


def verify_approval(secret: bytes, diff_bytes: bytes, supplied_hmac_hex: str) -> bool:
    expected = hmac.digest(secret, diff_bytes, "sha256").hex()
    return hmac.compare_digest(expected, supplied_hmac_hex)
