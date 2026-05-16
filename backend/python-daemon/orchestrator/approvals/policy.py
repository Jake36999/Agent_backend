from __future__ import annotations

from .models import ApprovalDecision, ApprovalReceipt, ApprovalRequirement

# Risk tiers that always require explicit approval before proceeding.
_APPROVAL_REQUIRED_TIERS = frozenset({"T3", "T4"})

# Capabilities explicitly allowlisted as network-capable without per-call approval.
# Populate this when real network-capable capabilities are production-approved.
_NETWORK_ALLOWLIST: frozenset[str] = frozenset()


def _needs_approval(req: ApprovalRequirement) -> tuple[bool, str]:
    """Return (needs_approval, reason) for the given requirement."""
    if req.risk_tier in _APPROVAL_REQUIRED_TIERS:
        return True, f"risk tier {req.risk_tier} requires approval"
    if req.network_access and req.capability_id not in _NETWORK_ALLOWLIST:
        return True, "network access requires approval"
    if req.writes_external_state:
        return True, "capability writes external state"
    if req.writes_files:
        return True, "capability mutates files"
    return False, ""


def evaluate_approval_requirement(req: ApprovalRequirement) -> ApprovalDecision:
    """Evaluate whether a capability may proceed without human approval.

    Rules:
    - T1/T2 read-only, no network, no external writes → NOT_REQUIRED (allowed).
    - T3+ → PENDING_APPROVAL (no approval system is wired yet; never silently allow).
    - network_access=True (not allowlisted) → PENDING_APPROVAL.
    - writes_external_state=True → PENDING_APPROVAL.
    - writes_files=True → PENDING_APPROVAL.

    Returns PENDING_APPROVAL when approval is needed but no system is configured.
    The caller must treat PENDING_APPROVAL as blocked until an approval arrives.
    """
    needed, reason = _needs_approval(req)

    if not needed:
        return ApprovalDecision(
            allowed=True,
            status="NOT_REQUIRED",
            reason="No approval required for this capability.",
            approval_id=None,
        )

    return ApprovalDecision(
        allowed=False,
        status="PENDING_APPROVAL",
        reason=f"Approval required: {reason}. No approval system is configured; request is held.",
        approval_id=None,
    )


def build_approval_receipt(
    req: ApprovalRequirement,
    decision: ApprovalDecision,
) -> ApprovalReceipt:
    return ApprovalReceipt(
        capability_id=req.capability_id,
        status=decision.status,
        allowed=decision.allowed,
        reason=decision.reason,
        approval_id=decision.approval_id,
        risk_tier=req.risk_tier,
    )
