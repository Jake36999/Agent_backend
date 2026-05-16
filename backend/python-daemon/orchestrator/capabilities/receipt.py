from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_RISK_TIERS = frozenset({"T1", "T2", "T3", "T4"})
_CAPABILITY_TYPES = frozenset({"adapter", "integration", "pipeline", "research", "skill"})

_SUMMARY_MAX = 200
_ARTIFACT_REFS_MAX = 20
_REF_MAX = 120


@dataclass(frozen=True)
class CapabilityExecutionReceipt:
    operation: str                          # always "capability.execute"
    capability_id: str                      # e.g. "code_intelligence.repo_context"
    capability_type: str                    # "adapter" | "pipeline" | "skill"
    risk_tier: str                          # "T1" | "T2" | "T3" | "T4"
    status: str                             # "OK" | "ERROR" | "POLICY_BLOCK"
    authorized: bool
    network_access: bool
    writes_external_state: bool
    approval_id: str | None
    artifact_refs: tuple[str, ...]
    summary: str


def build_receipt(
    *,
    capability_id: str,
    capability_type: str,
    risk_tier: str,
    status: str = "OK",
    authorized: bool = True,
    network_access: bool = False,
    writes_external_state: bool = False,
    approval_id: str | None = None,
    artifact_refs: list[str] | None = None,
    summary: str = "",
) -> CapabilityExecutionReceipt:
    if capability_type not in _CAPABILITY_TYPES:
        raise ValueError(f"capability_type must be one of {sorted(_CAPABILITY_TYPES)}")
    if risk_tier not in _RISK_TIERS:
        raise ValueError(f"risk_tier must be one of {sorted(_RISK_TIERS)}")
    refs = tuple(
        str(r)[:_REF_MAX]
        for r in (artifact_refs or [])[:_ARTIFACT_REFS_MAX]
    )
    return CapabilityExecutionReceipt(
        operation="capability.execute",
        capability_id=str(capability_id)[:120],
        capability_type=capability_type,
        risk_tier=risk_tier,
        status=str(status)[:32],
        authorized=bool(authorized),
        network_access=bool(network_access),
        writes_external_state=bool(writes_external_state),
        approval_id=str(approval_id)[:120] if approval_id is not None else None,
        artifact_refs=refs,
        summary=str(summary)[:_SUMMARY_MAX],
    )


def compact_receipt(receipt: CapabilityExecutionReceipt) -> dict[str, Any]:
    """Serialize to a JSON-safe dict. No source_path, no raw tool output."""
    return {
        "operation": receipt.operation,
        "capability_id": receipt.capability_id,
        "capability_type": receipt.capability_type,
        "risk_tier": receipt.risk_tier,
        "status": receipt.status,
        "authorized": receipt.authorized,
        "network_access": receipt.network_access,
        "writes_external_state": receipt.writes_external_state,
        "approval_id": receipt.approval_id,
        "artifact_refs": list(receipt.artifact_refs),
        "summary": receipt.summary,
    }
