from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

ApprovalStatus = Literal["APPROVED", "PENDING_APPROVAL", "POLICY_BLOCK", "NOT_REQUIRED"]


@dataclass(frozen=True)
class ApprovalRequirement:
    """Describes a capability that may need human approval before proceeding."""
    capability_id: str
    risk_tier: str                  # "T1" | "T2" | "T3" | "T4"
    reason: str
    requested_action: str
    writes_files: bool = False
    network_access: bool = False
    writes_external_state: bool = False


@dataclass(frozen=True)
class ApprovalDecision:
    """Result of evaluating whether a capability may proceed."""
    allowed: bool
    status: ApprovalStatus
    reason: str
    approval_id: str | None = None  # set when APPROVED; None otherwise


@dataclass(frozen=True)
class ApprovalReceipt:
    """Serialisable record of the approval decision for audit trails."""
    capability_id: str
    status: ApprovalStatus
    allowed: bool
    reason: str
    approval_id: str | None
    risk_tier: str

    def to_dict(self) -> dict:
        return {
            "capability_id": self.capability_id,
            "status": self.status,
            "allowed": self.allowed,
            "reason": self.reason,
            "approval_id": self.approval_id,
            "risk_tier": self.risk_tier,
        }
